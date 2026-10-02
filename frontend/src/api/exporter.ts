/**
 * 统一导出：所有模块共用这一套取数入口。
 *
 * - 范围（页面上选中的筛选条件）原样带给后端，与列表查询同一份口径；
 * - 批次未取完时按分片续取，从断掉的那一行接着取；
 * - 同一批重复导出后端只保留一份，前端直接拿到同批次下载；
 * - 文件名与表头顺序由后端按模块声明返回，兼容既有导出模板。
 */
import { request } from '@/api/client'

export interface ExportJob {
  id: string
  module: string
  status: 'running' | 'done' | 'failed'
  total: number
  cursor: number
  generation: number
  backfill_of: string | null
  file_name: string
  error: string
  done: boolean
  download_url: string
}

function buildQuery(module: string, filters: Record<string, string>): string {
  const params = new URLSearchParams()
  params.set('module', module)
  Object.entries(filters).forEach(([key, value]) => {
    const text = value.trim()
    if (text) params.set(key, text)
  })
  return params.toString()
}

async function postJson(path: string): Promise<ExportJob> {
  const response = await request(path, { method: 'POST' })
  if (!response.ok) {
    throw new Error(`导出请求失败（${response.status}），请稍后重试`)
  }
  return (await response.json()) as ExportJob
}

/**
 * 按当前页面范围发起导出并续取到完成，再触发浏览器下载。
 * 返回最终批次信息，供页面提示进度。
 */
export async function exportModule(
  module: string,
  filters: Record<string, string>,
  onProgress?: (done: number, total: number) => void,
): Promise<ExportJob> {
  let job = await postJson(`/api/exports?${buildQuery(module, filters)}`)
  onProgress?.(job.cursor, job.total)
  // 断在一半就从同一批次接着取，直到取完；重复点击会命中同一批次。
  while (job.status !== 'done') {
    if (job.status === 'failed') {
      throw new Error(job.error || '取数中断，可再次点击从断点继续')
    }
    job = await postJson(`/api/exports/${job.id}/resume`)
    onProgress?.(job.cursor, job.total)
  }
  triggerDownload(job.download_url, job.file_name)
  return job
}

function triggerDownload(url: string, fileName: string): void {
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

/** 换口径后回填存量导出（老包不动，另生成新口径包）。供运维入口调用。 */
export async function backfillExports(module?: string): Promise<{ backfilled: number }> {
  const query = module ? `?module=${encodeURIComponent(module)}` : ''
  const response = await request(`/api/exports/backfill${query}`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(`存量回填失败（${response.status}）`)
  }
  return (await response.json()) as { backfilled: number }
}
