# 性能监控指南

本文档介绍如何使用 SSD Knowledge Portal 的性能监控功能。

## 概述

性能监控系统自动收集和报告关键性能指标，帮助开发者识别和优化性能瓶颈。

## 功能特性

### 1. Web Vitals 监控

自动收集 Google 推荐的核心 Web 指标：

- **LCP (Largest Contentful Paint)**: 最大内容绘制时间
  - 优秀: ≤ 2.5s
  - 需要改进: 2.5s - 4.0s
  - 差: > 4.0s

- **FID (First Input Delay)**: 首次输入延迟
  - 优秀: ≤ 100ms
  - 需要改进: 100ms - 300ms
  - 差: > 300ms

- **CLS (Cumulative Layout Shift)**: 累积布局偏移
  - 优秀: ≤ 0.1
  - 需要改进: 0.1 - 0.25
  - 差: > 0.25

- **FCP (First Contentful Paint)**: 首次内容绘制
  - 优秀: ≤ 1.8s
  - 需要改进: 1.8s - 3.0s
  - 差: > 3.0s

- **TTFB (Time to First Byte)**: 首字节时间
  - 优秀: ≤ 800ms
  - 需要改进: 800ms - 1800ms
  - 差: > 1800ms

### 2. API 性能监控

自动跟踪所有 API 调用的性能：

- 调用次数
- 平均响应时间
- 最小/最大响应时间
- 错误率

### 3. 自定义指标

支持记录自定义性能指标：

- 组件渲染时间
- 业务逻辑执行时间
- 用户交互响应时间

## 使用方法

### 开发环境

在开发环境中，性能监控面板会自动显示在页面右下角。

#### 打开性能面板

点击右下角的图表图标 📊 打开性能监控面板。

#### 查看实时指标

面板会每秒更新一次，显示：
- Web Vitals 指标及其评级（绿色=优秀，黄色=需要改进，红色=差）
- API 调用统计
- 自定义指标

#### 导出性能数据

点击下载图标 ⬇️ 导出完整的性能数据为 JSON 文件，用于进一步分析。

### 编程接口

#### 记录自定义指标

```typescript
import { performanceMonitor } from './performanceMonitor';

// 记录简单指标
performanceMonitor.recordMetric('custom-operation', 150);

// 记录带元数据的指标
performanceMonitor.recordMetric('data-processing', 250, {
  itemCount: 100,
  cacheHit: true
});
```

#### 测量 API 调用

```typescript
import { performanceMonitor } from './performanceMonitor';

const result = await performanceMonitor.measureApiCall(
  'fetch-users',
  async () => {
    return await fetch('/api/users').then(r => r.json());
  },
  { endpoint: '/api/users' }
);
```

#### 使用 React Hooks

##### 测量组件渲染性能

```typescript
import { useRenderPerformance } from './usePerformance';

function MyComponent() {
  const renderCount = useRenderPerformance('MyComponent');
  
  return <div>Rendered {renderCount} times</div>;
}
```

##### 测量 Effect 执行时间

```typescript
import { useEffectPerformance } from './usePerformance';

function MyComponent() {
  useEffectPerformance('data-fetch', () => {
    // 执行耗时操作
    fetchData();
  }, []);
  
  return <div>Component</div>;
}
```

##### 测量 API 调用

```typescript
import { useApiPerformance } from './usePerformance';

function MyComponent() {
  const { measureApiCall } = useApiPerformance();
  
  const handleClick = async () => {
    const data = await measureApiCall('fetch-data', async () => {
      return await fetch('/api/data').then(r => r.json());
    });
  };
  
  return <button onClick={handleClick}>Fetch Data</button>;
}
```

#### 获取性能报告

```typescript
import { performanceMonitor } from './performanceMonitor';

// 获取完整报告
const report = performanceMonitor.getReport();
console.log('Web Vitals:', report.webVitals);
console.log('API Metrics:', report.apiMetrics);
console.log('Custom Metrics:', report.customMetrics);

// 获取页面加载指标
const pageLoad = performanceMonitor.getPageLoadMetrics();
console.log('DNS:', pageLoad.dns);
console.log('TCP:', pageLoad.tcp);
console.log('Request:', pageLoad.request);

// 获取所有原始指标
const metrics = performanceMonitor.getMetrics();

// 获取特定指标
const apiMetrics = performanceMonitor.getMetricsByName('api./api/workspaces');

// 获取平均值
const avgTime = performanceMonitor.getAverageMetric('api./api/workspaces');

// 获取统计摘要
const summary = performanceMonitor.getSummary();
```

#### 导出和日志

```typescript
import { performanceMonitor } from './performanceMonitor';

// 导出为 JSON
const json = performanceMonitor.exportMetrics();
console.log(json);

// 在控制台打印摘要
performanceMonitor.logSummary();
```

#### 控制监控

```typescript
import { performanceMonitor } from './performanceMonitor';

// 禁用监控
performanceMonitor.setEnabled(false);

// 启用监控
performanceMonitor.setEnabled(true);

// 清除所有指标
performanceMonitor.clearMetrics();

// 清理资源
performanceMonitor.destroy();
```

## 浏览器控制台访问

在开发环境中，可以通过浏览器控制台访问性能监控器：

```javascript
// 获取报告
window.performanceMonitor.getReport()

// 打印摘要
window.performanceMonitor.logSummary()

// 导出数据
window.performanceMonitor.exportMetrics()

// 获取所有指标
window.performanceMonitor.getMetrics()
```

## 性能优化建议

### 1. 优化 LCP

- 优化服务器响应时间
- 使用 CDN 加速资源加载
- 预加载关键资源
- 优化图片大小和格式
- 移除阻塞渲染的资源

### 2. 优化 FID

- 减少 JavaScript 执行时间
- 拆分长任务
- 使用 Web Workers 处理复杂计算
- 延迟加载非关键 JavaScript

### 3. 优化 CLS

- 为图片和视频设置尺寸
- 避免在现有内容上方插入内容
- 使用 transform 动画而非改变布局的属性
- 预留广告位空间

### 4. 优化 API 性能

- 实现请求缓存
- 使用 React Query 的缓存策略
- 减少不必要的 API 调用
- 实现请求去重
- 使用分页和虚拟滚动

### 5. 优化组件渲染

- 使用 React.memo 避免不必要的重渲染
- 使用 useMemo 和 useCallback 缓存计算结果
- 实现虚拟列表
- 懒加载组件

## 性能基准

### 目标指标

| 指标 | 目标值 | 当前值 | 状态 |
|------|--------|--------|------|
| LCP | < 2.5s | - | - |
| FID | < 100ms | - | - |
| CLS | < 0.1 | - | - |
| FCP | < 1.8s | - | - |
| TTFB | < 800ms | - | - |
| API 平均响应 | < 500ms | - | - |

### 页面加载目标

| 阶段 | 目标时间 |
|------|----------|
| DNS 查询 | < 50ms |
| TCP 连接 | < 100ms |
| 请求时间 | < 200ms |
| 响应时间 | < 500ms |
| DOM 解析 | < 500ms |
| 完全加载 | < 3s |

## 监控最佳实践

### 1. 定期检查

- 每周查看性能报告
- 关注性能趋势
- 识别性能退化

### 2. 性能预算

- 为关键指标设置阈值
- 在 CI/CD 中集成性能测试
- 性能退化时发出警报

### 3. 真实用户监控 (RUM)

- 收集真实用户的性能数据
- 分析不同设备和网络条件下的性能
- 识别影响用户体验的问题

### 4. 性能测试

- 在不同网络条件下测试
- 测试不同设备和浏览器
- 模拟高负载场景

## 故障排查

### 性能面板不显示

**问题**: 性能监控面板没有出现

**解决方案**:
1. 确认在开发环境中运行 (`npm run dev`)
2. 检查浏览器控制台是否有错误
3. 确认 `import.meta.env.DEV` 为 true

### 指标不更新

**问题**: 性能指标没有更新

**解决方案**:
1. 检查 `performanceMonitor.setEnabled(true)` 是否被调用
2. 确认浏览器支持 Performance API
3. 查看控制台是否有错误

### Web Vitals 显示 N/A

**问题**: Web Vitals 指标显示为 N/A

**解决方案**:
1. 等待页面完全加载
2. 与页面交互（触发 FID）
3. 某些指标需要时间才能收集到

## 生产环境

在生产环境中，性能监控面板会自动隐藏，但监控仍在后台运行。

### 集成分析服务

可以将性能数据发送到分析服务：

```typescript
import { performanceMonitor } from './performanceMonitor';

// 定期发送数据
setInterval(() => {
  const report = performanceMonitor.getReport();
  
  // 发送到分析服务
  fetch('/api/analytics/performance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(report)
  });
}, 5 * 60 * 1000); // 每 5 分钟
```

## 参考资料

- [Web Vitals](https://web.dev/vitals/)
- [Performance API](https://developer.mozilla.org/en-US/docs/Web/API/Performance)
- [React Performance Optimization](https://react.dev/learn/render-and-commit)
- [Chrome DevTools Performance](https://developer.chrome.com/docs/devtools/performance/)

## 更新日志

### 2024-01-01
- 初始版本
- 添加 Web Vitals 监控
- 添加 API 性能跟踪
- 添加自定义指标支持
- 添加性能监控面板
- 添加 React Hooks
