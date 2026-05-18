from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass
class SeriesSplit:
    series_id: str
    train_target: np.ndarray
    test_target: np.ndarray
    train_covariates: dict[str, np.ndarray]
    test_covariates: dict[str, np.ndarray]
    test_timestamps: np.ndarray

    @property
    def n_test_windows(self) -> int:
        return len(self.test_target)


def list_series_paths(data_dir: str | Path = "processed_data") -> list[Path]:
    data_dir = Path(data_dir)
    return sorted(data_dir.glob("load_*.csv"), key=lambda path: int(path.stem.split("_")[1]))


def load_series_splits(
    data_dir: str | Path = "processed_data",
    train_end: str | pd.Timestamp = "2013-12-31 23:00:00",
    test_start: str | pd.Timestamp = "2014-01-01 00:00:00",
    time_col: str = "time",
    target_col: str = "load",
    max_series: int | None = None,
    use_covariates: bool = True,
) -> tuple[list[SeriesSplit], list[str]]:
    train_end = pd.Timestamp(train_end)
    test_start = pd.Timestamp(test_start)

    series_splits: list[SeriesSplit] = []
    covariate_cols: list[str] | None = None

    for path in list_series_paths(data_dir)[:max_series]:
        df = pd.read_csv(path, parse_dates=[time_col]).sort_values(time_col).reset_index(drop=True)

        current_covariates = [col for col in df.columns if col not in [time_col, target_col]]
        if covariate_cols is None:
            covariate_cols = current_covariates
        elif current_covariates != covariate_cols:
            raise ValueError(f"Covariate columns differ in {path.name}")

        train_df = df[df[time_col] <= train_end].copy()
        test_df = df[df[time_col] >= test_start].copy()

        if len(train_df) == 0 or len(test_df) == 0:
            continue

        if use_covariates and covariate_cols:
            train_covariates = {
                col: train_df[col].to_numpy(dtype=np.float32, copy=True) for col in covariate_cols
            }
            test_covariates = {
                col: test_df[col].to_numpy(dtype=np.float32, copy=True) for col in covariate_cols
            }
        else:
            train_covariates = {}
            test_covariates = {}

        series_splits.append(
            SeriesSplit(
                series_id=path.stem,
                train_target=train_df[target_col].to_numpy(dtype=np.float32, copy=True),
                test_target=test_df[target_col].to_numpy(dtype=np.float32, copy=True),
                train_covariates=train_covariates,
                test_covariates=test_covariates,
                test_timestamps=test_df[time_col].to_numpy(copy=True),
            )
        )

    return series_splits, covariate_cols or []


def build_finetune_inputs(series_splits: Iterable[SeriesSplit]) -> list[dict]:
    inputs: list[dict] = []
    for split in series_splits:
        task: dict = {"target": split.train_target}
        if split.train_covariates:
            task["past_covariates"] = split.train_covariates
            task["future_covariates"] = {
                col: np.empty(0, dtype=np.float32) for col in split.train_covariates
            }
        inputs.append(task)
    return inputs


def load_base_pipeline(model_id: str = "amazon/chronos-2"):
    import torch
    from chronos import Chronos2Pipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipeline = Chronos2Pipeline.from_pretrained(model_id, device_map=device)
    return pipeline, device


def load_finetuned_pipeline(checkpoint_dir: str | Path):
    import torch
    from chronos import Chronos2Pipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipeline = Chronos2Pipeline.from_pretrained(str(checkpoint_dir), device_map=device)
    return pipeline, device


def finetune_pipeline(
    train_inputs: list[dict],
    prediction_length: int = 24,
    model_id: str = "amazon/chronos-2",
    finetune_mode: str = "lora",
    learning_rate: float | None = None,
    num_steps: int = 300,
    batch_size: int = 64,
    context_length: int = 168,
    output_dir: str | Path = "chronos2_ft_2012_2013",
    **trainer_kwargs,
):
    pipeline, device = load_base_pipeline(model_id=model_id)

    if learning_rate is None:
        learning_rate = 1e-5 if finetune_mode == "lora" else 1e-6

    finetuned = pipeline.fit(
        inputs=train_inputs,
        prediction_length=prediction_length,
        finetune_mode=finetune_mode,
        learning_rate=learning_rate,
        num_steps=num_steps,
        batch_size=batch_size,
        context_length=context_length,
        output_dir=output_dir,
        remove_printer_callback=True,
        report_to=[],
        logging_steps=max(1, num_steps // 10),
        save_strategy="steps",
        save_steps=max(1, num_steps),
        **trainer_kwargs,
    )
    return finetuned, device


def _build_window_task(split: SeriesSplit, start: int, prediction_length: int, max_context: int = 168) -> dict:
    end = start + prediction_length
    context_target = np.concatenate([split.train_target, split.test_target[:start]]).astype(np.float32, copy=False)
    context_target = context_target[-max_context:]
    task: dict = {"target": context_target}

    if split.train_covariates:
        past_covariates = {
            col: np.concatenate([split.train_covariates[col], split.test_covariates[col][:start]]).astype(np.float32, copy=False)[
                -max_context:
            ]
            for col in split.train_covariates
        }
        future_covariates = {
            col: split.test_covariates[col][start:end].astype(np.float32, copy=False)
            for col in split.train_covariates
        }
        task["past_covariates"] = past_covariates
        task["future_covariates"] = future_covariates

    return task


def build_window_task(split: SeriesSplit, start: int, prediction_length: int, max_context: int = 168) -> dict:
    return _build_window_task(
        split=split,
        start=start,
        prediction_length=prediction_length,
        max_context=max_context,
    )


def _make_task_row_labels(task: dict) -> list[str]:
    target = np.asarray(task["target"])
    n_targets = 1 if target.ndim == 1 else target.shape[0]

    past_covariates = task.get("past_covariates", {})
    future_covariates = task.get("future_covariates", {})
    past_keys = sorted(past_covariates.keys())
    future_keys = sorted(future_covariates.keys())

    past_only_keys = [key for key in past_keys if key not in future_keys]
    known_future_keys = [key for key in past_keys if key in future_keys]

    target_labels = ["target"] if n_targets == 1 else [f"target_{idx}" for idx in range(n_targets)]
    covariate_labels = [f"past_only:{key}" for key in past_only_keys] + [
        f"known_future:{key}" for key in known_future_keys
    ]
    return target_labels + covariate_labels


def extract_prediction_attention(
    pipeline,
    task: dict,
    prediction_length: int,
    context_length: int | None = None,
) -> dict:
    import math

    import torch
    from torch.utils.data import DataLoader

    from chronos.chronos2.dataset import Chronos2Dataset, DatasetMode

    if prediction_length > pipeline.model_prediction_length:
        raise ValueError(
            "This helper captures attentions from a single Chronos-2 forward pass. "
            f"Use prediction_length <= {pipeline.model_prediction_length}, "
            f"but found {prediction_length}."
        )

    if context_length is None:
        context_length = pipeline.model_context_length
    context_length = min(context_length, pipeline.model_context_length)

    dataset = Chronos2Dataset.convert_inputs(
        inputs=[task],
        context_length=context_length,
        prediction_length=prediction_length,
        batch_size=1,
        output_patch_size=pipeline.model_output_patch_size,
        mode=DatasetMode.TEST,
    )
    loader = DataLoader(
        dataset,
        batch_size=None,
        num_workers=0,
        pin_memory=pipeline.model.device.type == "cuda",
        shuffle=False,
        drop_last=False,
    )
    batch = next(iter(loader))

    context = batch["context"].to(device=pipeline.model.device, dtype=torch.float32)
    group_ids = batch["group_ids"].to(pipeline.model.device)
    future_covariates = batch["future_covariates"].to(device=pipeline.model.device, dtype=torch.float32)
    num_output_patches = math.ceil(prediction_length / pipeline.model_output_patch_size)

    with torch.no_grad():
        outputs = pipeline.model(
            context=context,
            group_ids=group_ids,
            future_covariates=future_covariates,
            num_output_patches=num_output_patches,
            output_attentions=True,
        )

    time_attn = torch.stack([tensor.detach().cpu() for tensor in outputs.enc_time_self_attn_weights], dim=0)
    group_attn = torch.stack([tensor.detach().cpu() for tensor in outputs.enc_group_self_attn_weights], dim=0)

    use_reg = int(pipeline.model.chronos_config.use_reg_token)
    seq_tokens = int(time_attn.shape[-1])
    num_context_patches = seq_tokens - use_reg - num_output_patches
    token_labels = [f"context_patch_{idx}" for idx in range(num_context_patches)]
    if use_reg:
        token_labels.append("REG")
    token_labels.extend(f"future_patch_{idx}" for idx in range(num_output_patches))

    return {
        "task": task,
        "quantile_preds": outputs.quantile_preds.detach().cpu(),
        "time_attn": time_attn,
        "group_attn": group_attn,
        "row_labels": _make_task_row_labels(task),
        "token_labels": token_labels,
        "context": batch["context"].cpu(),
        "future_covariates": batch["future_covariates"].cpu(),
        "group_ids": batch["group_ids"].cpu(),
        "target_idx_ranges": batch["target_idx_ranges"],
        "meta": {
            "n_layers": int(time_attn.shape[0]),
            "group_size": int(time_attn.shape[1]),
            "n_heads": int(time_attn.shape[2]),
            "seq_tokens": seq_tokens,
            "num_context_patches": num_context_patches,
            "num_output_patches": num_output_patches,
            "input_patch_size": int(pipeline.model.chronos_config.input_patch_size),
            "output_patch_size": int(pipeline.model.chronos_config.output_patch_size),
            "time_attn_shape": tuple(time_attn.shape),
            "group_attn_shape": tuple(group_attn.shape),
        },
    }


def extract_window_attention(
    pipeline,
    split: SeriesSplit,
    start: int,
    prediction_length: int = 24,
    max_context: int = 168,
) -> dict:
    end = start + prediction_length
    task = build_window_task(
        split=split,
        start=start,
        prediction_length=prediction_length,
        max_context=max_context,
    )
    attention_bundle = extract_prediction_attention(
        pipeline=pipeline,
        task=task,
        prediction_length=prediction_length,
        context_length=max_context,
    )
    attention_bundle.update(
        {
            "series_id": split.series_id,
            "window_start": start,
            "window_end": end,
            "window_timestamps": split.test_timestamps[start:end],
            "window_actual": split.test_target[start:end],
        }
    )
    return attention_bundle


def _attention_bundle_fingerprint(attention_bundle: dict) -> str:
    time_attn_bytes = attention_bundle["time_attn"].contiguous().numpy().tobytes()
    group_attn_bytes = attention_bundle["group_attn"].contiguous().numpy().tobytes()
    return hashlib.sha1(time_attn_bytes + group_attn_bytes).hexdigest()[:16]


def extract_window_attentions(
    pipeline,
    split: SeriesSplit,
    prediction_length: int = 24,
    max_context: int = 168,
    window_stride: int | None = None,
    window_starts: Iterable[int] | None = None,
    max_windows: int | None = None,
) -> list[dict]:
    if window_stride is None:
        window_stride = prediction_length

    if window_starts is None:
        max_start = len(split.test_target) - prediction_length
        if max_start < 0:
            return []
        window_starts = range(0, max_start + 1, window_stride)

    attention_bundles: list[dict] = []
    for window_idx, start in enumerate(window_starts):
        if max_windows is not None and len(attention_bundles) >= max_windows:
            break

        end = start + prediction_length
        if start < 0 or end > len(split.test_target):
            continue

        attention_bundle = extract_window_attention(
            pipeline=pipeline,
            split=split,
            start=start,
            prediction_length=prediction_length,
            max_context=max_context,
        )
        attention_bundle["window_idx"] = len(attention_bundles)
        attention_bundle["attention_fingerprint"] = _attention_bundle_fingerprint(attention_bundle)
        attention_bundles.append(attention_bundle)

    return attention_bundles


def summarize_window_attentions(attention_bundles: Iterable[dict], target_idx: int = 0) -> pd.DataFrame:
    rows: list[dict] = []

    for attention_bundle in attention_bundles:
        group_attn_mean = attention_bundle["group_attn"].float().mean(dim=(0, 1, 2))
        row_labels = attention_bundle["row_labels"]

        target_query_label = row_labels[target_idx]
        top_source_idx = int(group_attn_mean[target_idx].argmax().item())

        rows.append(
            {
                "series_id": attention_bundle["series_id"],
                "window_idx": attention_bundle.get("window_idx"),
                "window_start": attention_bundle["window_start"],
                "window_end": attention_bundle["window_end"],
                "timestamp_start": str(pd.Timestamp(attention_bundle["window_timestamps"][0])),
                "timestamp_end": str(pd.Timestamp(attention_bundle["window_timestamps"][-1])),
                "attention_fingerprint": attention_bundle["attention_fingerprint"],
                "n_row_labels": len(row_labels),
                "n_token_labels": len(attention_bundle["token_labels"]),
                "target_query_label": target_query_label,
                "top_source_label": row_labels[top_source_idx],
                "top_source_attention": float(group_attn_mean[target_idx, top_source_idx].item()),
                "time_attn_shape": str(tuple(attention_bundle["time_attn"].shape)),
                "group_attn_shape": str(tuple(attention_bundle["group_attn"].shape)),
            }
        )

    return pd.DataFrame(rows)


def rolling_evaluate(
    pipeline,
    series_splits: list[SeriesSplit],
    prediction_length: int = 24,
    quantile_levels: list[float] | None = None,
    batch_size: int = 64,
    window_stride: int = 24,
    max_windows: int | None = None,
    max_context: int = 168,
    series_ids: list[str] | None = None,
    max_series: int | None = None,
) -> pd.DataFrame:
    if quantile_levels is None:
        quantile_levels = [0.1, 0.5, 0.9]

    if series_ids is not None:
        allowed_ids = set(series_ids)
        series_splits = [split for split in series_splits if split.series_id in allowed_ids]

    if max_series is not None:
        series_splits = series_splits[:max_series]

    if not series_splits:
        return pd.DataFrame(columns=["series_id", "timestamp", "actual", "predictions", "window_idx", "horizon_step"])

    results: list[pd.DataFrame] = []
    max_possible_windows = max(len(split.test_target) // prediction_length for split in series_splits)
    n_windows = min(max_possible_windows, max_windows) if max_windows is not None else max_possible_windows

    for window_idx in range(n_windows):
        start = window_idx * window_stride
        end = start + prediction_length

        batch_tasks: list[dict] = []
        batch_meta: list[tuple[str, np.ndarray, np.ndarray, int]] = []

        def flush_batch():
            nonlocal batch_tasks, batch_meta
            if not batch_tasks:
                return

            quantiles, mean = pipeline.predict_quantiles(
                batch_tasks,
                prediction_length=prediction_length,
                quantile_levels=quantile_levels,
                batch_size=batch_size,
            )

            for meta, q_tensor, mean_tensor in zip(batch_meta, quantiles, mean):
                series_id, timestamps, actual, current_window_idx = meta
                q = q_tensor.squeeze(0).cpu().numpy()
                pred = mean_tensor.squeeze(0).cpu().numpy()

                frame = pd.DataFrame(
                    {
                        "series_id": series_id,
                        "timestamp": timestamps,
                        "actual": actual,
                        "predictions": pred,
                        "window_idx": current_window_idx,
                        "horizon_step": np.arange(1, prediction_length + 1),
                    }
                )
                for q_idx, q_level in enumerate(quantile_levels):
                    frame[str(q_level)] = q[:, q_idx]
                results.append(frame)

            batch_tasks = []
            batch_meta = []

        for split in series_splits:
            if end > len(split.test_target):
                continue

            batch_tasks.append(_build_window_task(split, start=start, prediction_length=prediction_length, max_context=max_context))
            batch_meta.append(
                (
                    split.series_id,
                    split.test_timestamps[start:end],
                    split.test_target[start:end],
                    window_idx,
                )
            )

            if len(batch_tasks) >= batch_size:
                flush_batch()

        flush_batch()

    if not results:
        return pd.DataFrame(columns=["series_id", "timestamp", "actual", "predictions", "window_idx", "horizon_step"])

    return pd.concat(results, ignore_index=True)


def summarize_results(results: pd.DataFrame) -> pd.Series:
    err = results["predictions"] - results["actual"]
    nonzero_actual = results["actual"].replace(0, np.nan)
    summary = pd.Series(
        {
            "n_rows": len(results),
            "mae": err.abs().mean(),
            "rmse": np.sqrt(np.mean(err**2)),
            "mape": (err.abs() / nonzero_actual.abs()).mean() * 100,
        }
    )
    return summary
