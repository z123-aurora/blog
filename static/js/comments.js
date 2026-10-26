/* 文章留言区：
 * 读：Web SDK 的 callFunction 调用云函数 listComments（所有人含匿名访客可读）
 * 写：客户端没有数据库写权限，统一走云函数 addComment 落库
 */
(function () {
    "use strict";

    var ENV_ID = "blog-d3gd2wmcb82959ac9";
    var ADD_FUNCTION = "addComment";
    var LIST_FUNCTION = "listComments";

    var root = document.getElementById("comments");
    if (!root || typeof cloudbase === "undefined") {
        return;
    }

    var articleId = root.getAttribute("data-article-id");
    var listEl = document.getElementById("comment-list");
    var countEl = document.getElementById("comment-count");
    var formEl = document.getElementById("comment-form");
    var nicknameEl = document.getElementById("comment-nickname");
    var contentEl = document.getElementById("comment-content");
    var statusEl = document.getElementById("comment-status");
    var submitEl = document.getElementById("comment-submit");

    var app = cloudbase.init({ env: ENV_ID });
    var auth = app.auth({ persistence: "local" });
    var loginPromise = null;

    // 未登录时走匿名登录，保证「所有人可读」能生效
    // 兼容 SDK v1（anonymousAuthProvider）与 v2（signInAnonymously）两种 API
    function ensureLogin() {
        if (!loginPromise) {
            loginPromise = Promise.resolve(
                typeof auth.getLoginState === "function" ? auth.getLoginState() : null
            )
                .then(function (state) {
                    if (state) {
                        return state;
                    }
                    if (typeof auth.anonymousAuthProvider === "function") {
                        return auth.anonymousAuthProvider().signIn();
                    }
                    if (typeof auth.signInAnonymously === "function") {
                        return auth.signInAnonymously();
                    }
                    throw new Error("当前 SDK 版本不支持匿名登录");
                })
                .catch(function (err) {
                    loginPromise = null; // 失败后允许下次重试
                    throw err;
                });
        }
        return loginPromise;
    }

    function setStatus(text, type) {
        statusEl.textContent = text || "";
        statusEl.className = "comment-status" + (type ? " is-" + type : "");
    }

    function formatTime(value) {
        if (!value) {
            return "";
        }
        var date = value instanceof Date ? value : new Date(value);
        if (isNaN(date.getTime())) {
            return "";
        }
        function pad(n) {
            return n < 10 ? "0" + n : String(n);
        }
        return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate()) +
            " " + pad(date.getHours()) + ":" + pad(date.getMinutes());
    }

    function showPlaceholder(text) {
        listEl.innerHTML = "";
        var li = document.createElement("li");
        li.className = "comment-empty";
        li.textContent = text;
        listEl.appendChild(li);
    }

    function renderComments(items) {
        listEl.innerHTML = "";
        countEl.textContent = String(items.length);

        if (!items.length) {
            showPlaceholder("还没有留言，来说两句吧");
            return;
        }

        items.forEach(function (item) {
            var li = document.createElement("li");
            li.className = "comment-item";

            var head = document.createElement("div");
            head.className = "comment-head";

            var name = document.createElement("strong");
            name.className = "comment-name";
            name.textContent = item.nickname || "匿名读者";

            var time = document.createElement("span");
            time.className = "comment-time";
            time.textContent = formatTime(item.createdAt);

            var body = document.createElement("p");
            body.className = "comment-body";
            body.textContent = item.content || "";

            head.appendChild(name);
            head.appendChild(time);
            li.appendChild(head);
            li.appendChild(body);
            listEl.appendChild(li);
        });
    }

    function loadComments() {
        showPlaceholder("正在加载留言…");
        return ensureLogin()
            .then(function () {
                return app.callFunction({
                    name: LIST_FUNCTION,
                    data: { articleId: articleId }
                });
            })
            .then(function (res) {
                var result = res.result || {};
                if (!result.ok) {
                    throw new Error(result.message || "加载失败");
                }
                renderComments(result.data || []);
            })
            .catch(function (err) {
                console.error("[comments] 加载失败", err);
                showPlaceholder("留言加载失败：" + ((err && err.message) || "未知错误"));
            });
    }

    formEl.addEventListener("submit", function (event) {
        event.preventDefault();

        var content = contentEl.value.trim();
        if (!content) {
            setStatus("留言内容不能为空", "error");
            contentEl.focus();
            return;
        }

        submitEl.disabled = true;
        setStatus("正在发表…", "");

        ensureLogin()
            .then(function () {
                return app.callFunction({
                    name: ADD_FUNCTION,
                    data: {
                        articleId: articleId,
                        nickname: nicknameEl.value.trim(),
                        content: content
                    }
                });
            })
            .then(function (res) {
                var result = res.result || {};
                if (!result.ok) {
                    throw new Error(result.message || "发表失败");
                }
                contentEl.value = "";
                setStatus("留言已发表", "success");
                return loadComments();
            })
            .catch(function (err) {
                console.error("[comments] 发表失败", err);
                setStatus("发表失败：" + ((err && err.message) || "未知错误"), "error");
            })
            .then(function () {
                submitEl.disabled = false;
            });
    });

    loadComments();
})();
