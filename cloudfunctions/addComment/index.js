// 云函数 addComment（普通云函数，供 Web SDK callFunction 调用）
// 当前环境是 CloudBase PostgreSQL（PG 模式），没有可直接连接的数据库账号，
// 云函数改用服务端 API Key 通过数据库网关写入 comments 表。
// 客户端没有数据库写权限，所有留言写入都必须经过这里。
const ENV_ID = process.env.TCB_ENV_ID || "blog-d3gd2wmcb82959ac9";
const API_KEY = process.env.TCB_API_KEY || "";
const REST_BASE = `https://${ENV_ID}.api.tcloudbasegateway.com/v1/rdb/rest`;

const MAX_CONTENT_LENGTH = 500;
const MAX_NICKNAME_LENGTH = 20;

function normalize(value, maxLength) {
  return String(value == null ? "" : value).trim().slice(0, maxLength);
}

exports.main = async (event = {}) => {
  const articleId = normalize(event.articleId, 32);
  const content = normalize(event.content, MAX_CONTENT_LENGTH);
  const nickname = normalize(event.nickname, MAX_NICKNAME_LENGTH) || "匿名读者";

  if (!/^\d+$/.test(articleId)) {
    return { ok: false, message: "缺少有效的文章 ID" };
  }
  if (!content) {
    return { ok: false, message: "留言内容不能为空" };
  }
  if (!API_KEY) {
    return { ok: false, message: "云函数缺少 TCB_API_KEY 环境变量" };
  }

  const res = await fetch(`${REST_BASE}/comments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
      Prefer: "return=representation",
    },
    body: JSON.stringify({ article_id: articleId, nickname, content }),
  });

  if (!res.ok) {
    const detail = await res.text();
    return { ok: false, message: `写入失败（HTTP ${res.status}）${detail.slice(0, 200)}` };
  }

  const rows = await res.json();
  return { ok: true, id: String(rows[0].id) };
};
