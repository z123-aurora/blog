// ============================================================
// 实验第 9 项：把同一套后端接到小程序
// 文件：miniprogram/app.js
// 只需在 onLaunch 里加一行 wx.cloud.init({ env: '环境ID' })，即可
// 直接复用同一环境下的云函数、数据库与存储，后端完全不需要重写。
// ============================================================

// 与 Flask 站点 / Web 端完全相同的 CloudBase 环境
const ENV_ID = 'blog-d3gd2wmcb82959ac9';

App({
  onLaunch: function () {
    if (!wx.cloud) {
      console.error('[cloud] 请使用 2.2.3 或以上的基础库以使用云能力');
      return;
    }

    // 关键的一行：指定与环境一致的环境ID，之后 wx.cloud.callFunction /
    // wx.cloud.database / wx.cloud.uploadFile 都会落到这个环境
    wx.cloud.init({ env: ENV_ID, traceUser: true });

    console.log('[cloud] 环境初始化完成：' + ENV_ID);
  },

  globalData: {
    envId: ENV_ID
  }
});
