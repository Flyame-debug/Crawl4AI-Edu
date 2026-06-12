<template>
  <div class="guide-page">
    <h2>操作指南</h2>
    <section>
      <h3>快速开始</h3>
      <p>登录成功后，您可以通过左侧导航栏进入不同的功能模块，例如首页、模板管理、新建模板和任务监控。</p>
    </section>

    <section>
      <h3>模板管理</h3>
      <p>在“模板页面”中，您可以查看已有的模板，进行编辑或删除操作。</p>
    </section>

    <section>
      <h3>新建模板</h3>
      <p>点击“新建模板”可以创建新的采集任务模板，配置采集规则和参数。</p>
    </section>

    <section>
      <h3>任务监控</h3>
      <p>在“任务监控”中，您可以查看采集任务的执行状态，监控进度并查看结果。</p>
    </section>

    <section>
      <h3>常见问题</h3>
      <ul>
        <li>如何退出登录？ → 点击右上角用户头像，选择“退出登录”。</li>
        <li>如何修改密码？ → 后续会在用户菜单中提供“修改密码”功能。</li>
        <li>如何联系管理员？ → 请通过系统提供的反馈渠道。</li>
      </ul>
    </section>
  </div>
</template>

<script>
export default {
  name: 'GuidePage'
}
</script>

<style scoped>
.guide-page {
  padding: 20px;
}
h2 {
  margin-bottom: 20px;
}
section {
  margin-bottom: 20px;
}
</style>
