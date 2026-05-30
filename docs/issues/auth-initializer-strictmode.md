# F5 刷新退出登录问题

## 现象

浏览器 F5 刷新后页面短暂显示目标页，随后跳转到 `/login`。后端日志显示 `/auth/refresh` 和 `/auth/me` 均返回 200。

## 根因

React StrictMode 开发模式下双挂载组件。`AuthInitializer` 的 `useEffect` 在第一挂载中启动异步 refresh，cleanup 设置 `cancelled=true`。第二挂载以某种方式"跳过"等待 → 子组件在没有 token 的情况下渲染 → API 请求 401 → axios 拦截器跳 `/login`。

## 错误方案

| 方案 | 为什么失败 |
|------|-----------|
| `useRef` 防重 + else 分支设 `setChecking(false)` | 第二挂载立即结束 loading，但 refresh 仍在飞行中 |
| 模块变量 `didRefresh` | StrictMode 不重载模块，变量保持 `true`，第二挂载跳过 |
| 移除 `didRefresh` 让两次都调 refresh | 第一次已撤销 token，第二次调用失败 401 |

## 正确方案

模块级 Promise，所有挂载实例共享：

```ts
let refreshPromise: Promise<void> | null = null;

// 在 useEffect 中:
if (!refreshPromise) {
  refreshPromise = doRefresh(setAccessToken, setUser);
}
refreshPromise.then(() => {
  if (!cancelled) setChecking(false);
});
```

- 第一次挂载创建 Promise 并启动 refresh
- 第二次挂载复用同一个 Promise，`.then()` 等待完成后结束 loading
- `setChecking(false)` 只在实际 refresh 完成后执行

## 关键教训

StrictMode 下异步初始化不能用防重 + 立即结束 loading。必须让所有挂载实例等待同一个异步操作完成。

## 相关文件

- `frontend/src/components/auth/AuthInitializer.tsx`
- `frontend/src/stores/authStore.ts`
- `frontend/src/api/client.ts`
