/**
 * 아이콘 PNG를 표시 사이즈(64x64, retina용)에 맞춰 리사이즈하고 WebP를 함께 생성한다.
 * 실제 표시는 18~32px이지만 retina/HiDPI 대응 + 살짝 여유를 두어 64x64를 유지한다.
 *
 * 사용: node scripts/optimize-icons.mjs
 */
import { promises as fs } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import sharp from 'sharp'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')
const ICON_DIR = path.join(ROOT, 'src', 'assets', 'images', 'icons')
const TARGET_SIZE = 64

async function processOne(file) {
  const full = path.join(ICON_DIR, file)
  const stat = await fs.stat(full)
  if (!stat.isFile() || !file.toLowerCase().endsWith('.png')) return null

  const before = stat.size

  const img = sharp(full).resize(TARGET_SIZE, TARGET_SIZE, {
    fit: 'inside',
    withoutEnlargement: true,
  })

  const pngBuf = await img.clone().png({ compressionLevel: 9, palette: true }).toBuffer()
  await fs.writeFile(full, pngBuf)

  const webpBuf = await img.clone().webp({ quality: 90 }).toBuffer()
  const webpPath = full.replace(/\.png$/i, '.webp')
  await fs.writeFile(webpPath, webpBuf)

  return {
    file,
    beforeKB: (before / 1024).toFixed(1),
    pngKB: (pngBuf.length / 1024).toFixed(1),
    webpKB: (webpBuf.length / 1024).toFixed(1),
  }
}

const entries = await fs.readdir(ICON_DIR)
const results = []
for (const f of entries) {
  const r = await processOne(f)
  if (r) results.push(r)
}

console.table(results)
const totalBefore = results.reduce((s, r) => s + Number(r.beforeKB), 0)
const totalPng = results.reduce((s, r) => s + Number(r.pngKB), 0)
console.log(`\nTotal PNG:  ${totalBefore.toFixed(1)} KB → ${totalPng.toFixed(1)} KB`)
