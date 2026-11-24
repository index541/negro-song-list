// 歌える曲リスト管理: プッシュ通知用 Service Worker
self.addEventListener("push", function (e) {
  var d = { title: "🎤 新しい歌唱リクエスト", body: "", url: "admin.html" };
  try { if (e.data) { var j = e.data.json(); for (var k in j) d[k] = j[k]; } } catch (err) {}
  e.waitUntil(self.registration.showNotification(d.title, {
    body: d.body,
    icon: "icon-192.png",
    badge: "icon-192.png",
    data: { url: d.url }
  }));
});
self.addEventListener("notificationclick", function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || "admin.html";
  e.waitUntil(clients.openWindow(url));
});
