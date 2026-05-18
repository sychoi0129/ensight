/**
 * ECharts tree-shaking 진입점.
 * 전체 echarts(약 1.1MB)를 통째 로드하지 않고 실제 사용하는 차트/컴포넌트만 등록한다.
 * 새 차트 종류를 쓰게 되면 여기에 추가해야 한다.
 */
import * as echarts from 'echarts/core'
import { BarChart, LineChart, ScatterChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer,
])

export default echarts
export * from 'echarts/core'
