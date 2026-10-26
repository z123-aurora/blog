// 留言页：直接调用 Flask 站点同一环境下的云函数，不写任何后端
const app = getApp();

Page({
  data: {
    envId: '',
    list: [],
    nickname: '',
    content: '',
    loading: false,
    log: []
  },

  onLoad: function () {
    this.setData({ envId: app.globalData.envId });
    this.loadComments();
  },

  // 读：调用云函数 listComments
  loadComments: function () {
    const that = this;
    that.setData({ loading: true });
    that.pushLog('[callFunction] listComments articleId=2');

    wx.cloud.callFunction({
      name: 'listComments',
      data: { articleId: '2' }
    }).then(function (res) {
      const result = res.result || {};
      that.pushLog('[返回] ' + JSON.stringify(result).slice(0, 300));
      that.setData({
        list: result.data || [],
        loading: false
      });
    }).catch(function (err) {
      that.pushLog('[失败] ' + (err && err.errMsg ? err.errMsg : String(err)));
      that.setData({ loading: false });
    });
  },

  onNicknameInput: function (e) {
    this.setData({ nickname: e.detail.value });
  },

  onContentInput: function (e) {
    this.setData({ content: e.detail.value });
  },

  // 写：调用云函数 addComment
  submit: function () {
    const that = this;
    const content = (that.data.content || '').trim();
    if (!content) {
      wx.showToast({ title: '请先写点内容', icon: 'none' });
      return;
    }

    that.pushLog('[callFunction] addComment content=' + content);
    wx.cloud.callFunction({
      name: 'addComment',
      data: {
        articleId: '2',
        nickname: (that.data.nickname || '').trim() || '微信用户',
        content: content
      }
    }).then(function (res) {
      that.pushLog('[返回] ' + JSON.stringify(res.result));
      if (res.result && res.result.ok) {
        wx.showToast({ title: '留言成功', icon: 'success' });
        that.setData({ content: '' });
        that.loadComments();
      } else {
        wx.showToast({ title: (res.result && res.result.message) || '写入失败', icon: 'none' });
      }
    }).catch(function (err) {
      that.pushLog('[失败] ' + (err && err.errMsg ? err.errMsg : String(err)));
    });
  },

  // 把调用过程同时打印到控制台（开发者工具 Console 可见）
  pushLog: function (line) {
    console.log(line);
    const log = this.data.log.concat([line]).slice(-12);
    this.setData({ log: log });
  }
});
