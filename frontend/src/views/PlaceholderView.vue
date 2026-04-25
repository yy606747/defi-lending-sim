<template>
  <div class="placeholder-page">
    <div class="placeholder-inner">
      <div class="placeholder-icon">
        <svg viewBox="0 0 48 48" fill="none">
          <rect x="6" y="6" width="36" height="36" rx="10" stroke="currentColor" stroke-width="1.5" stroke-dasharray="4 3"/>
          <path d="M18 24h12M24 18v12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      <h3>功能开发中</h3>
      <p>该模块正在建设，敬请期待</p>
    </div>
  </div>
</template>

<style scoped>
.placeholder-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
.placeholder-inner {
  text-align: center;
}
.placeholder-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  color: var(--text-muted);
  opacity: 0.4;
}
.placeholder-icon svg {
  width: 100%;
  height: 100%;
}
.placeholder-inner h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 6px;
}
.placeholder-inner p {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
