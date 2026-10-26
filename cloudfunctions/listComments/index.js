// 云函数 listComments（普通云函数，供 Web SDK callFunction 调用）
// 通过服务端 API Key 从数据库网关读取 comments 表，所有人（含匿名访客）可读。
const ENV_ID = process.env.TCB_ENV_ID || "blog-d3gd2wmcb82959ac9";
const API_KEY = process.env.TCB_API_KEY || "";
const REST_BASE = `https://${ENV_ID}.api.tcloudbasegateway.com/v1/rdb/rest`;

const PAGE_SIZE = 50;

exports.main = async (event = {}) => {
  const articleId = String(event.articleId == null ? "" : event.articleId).trim();

  if (!/^\d+$/.test(articleId)) {
    return { ok: false, message: "缺少有效的文章 ID", data: [] };
  }
  if (!API_KEY) {
    return { ok: false, message: "云函数缺少 TCB_API_KEY 环境变量", data: [] };
  }

  const query = new URLSearchParams({
    select: "id,nickname,content,created_at",
    article_id: `eq.${articleId}`,
    order: "created_at.desc,id.desc",
    limit: String(PAGE_SIZE),
  });

  const res = await fetch(`${REST_BASE}/comments?${query.toString()}`, {
    headers: { Authorization: `Bearer ${API_KEY}` },
  });

  if (!res.ok) {
    const detail = await res.text();
    return { ok: false, message: `读取失败（HTTP ${res.status}）${detail.slice(0, 200)}`, data: [] };
  }

  const rows = await res.json();
  return {
    ok: true,
    data: rows.map((row) => ({
      id: String(row.id),
      nickname: row.nickname,
      content: row.content,
      createdAt: row.created_at,
    })),
  };
};
