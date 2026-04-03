import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'RodSki 测试用例编写指南',
  description: 'RodSki v3.0+ 测试用例编写完全指南 v3.4',
  srcDir: '.',

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text y="26" font-size="28">📋</text></svg>' }],
  ],

  themeConfig: {
    logo: { src: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text y="26" font-size="28">📋</text></svg>', width: 24, height: 24 },

    nav: [
      { text: '首页', link: '/' },
      { text: 'v3.4 · 2026-04-02', link: '/' },
    ],

    sidebar: [
      {
        text: '📖 指南目录',
        items: [
          { text: 'README — 总入口', link: '/README' },
        ],
      },
      {
        text: '第一章：基础',
        items: [
          { text: '§1 核心概念', link: '/01-core-concepts' },
          { text: '§2 目录结构', link: '/02-directory-structure' },
          { text: '§3 Case XML', link: '/03-case-xml' },
          { text: '§4 model.xml', link: '/04-model-xml' },
          { text: '§5 数据表 XML', link: '/05-data-tables' },
          { text: '§6 GlobalValue XML', link: '/06-global-value' },
          { text: '§7 数据引用与变量解析', link: '/07-data-reference' },
        ],
      },
      {
        text: '第二章：参考',
        items: [
          { text: '§8 关键字手册', link: '/08-keyword-reference' },
          { text: '§9 完整示例', link: '/09-complete-example' },
          { text: '§10 固定与动态测试步骤', link: '/10-dynamic-steps' },
          { text: '§11 视觉定位器', link: '/11-vision-locators' },
          { text: '§12 桌面端自动化', link: '/12-desktop-automation' },
          { text: '§13 if/else 流程控制', link: '/13-if-else' },
        ],
      },
      {
        text: '附录',
        items: [
          { text: '常见问题 FAQ', link: '/appendix-faq' },
          { text: '关键字速查清单', link: '/appendix-keyword-ref' },
          { text: '测试结果 XML', link: '/appendix-result-xml' },
        ],
      },
    ],

    editLink: {
      pattern: 'https://github.com/your-repo/edit/main/docs/user-guides/TEST_CASE_WRITING_GUIDE/:path',
      text: '在 GitHub 上编辑此页',
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/your-repo/rodski' },
    ],

    search: {
      provider: 'local',
    },

    footer: {
      message: 'RodSki 测试用例编写指南 v3.4',
      copyright: '2026-04-02 · RodSki v3.0+',
    },
  },

  markdown: {
    lineNumbers: true,
    theme: {
      light: 'github-light',
      dark: 'github-dark',
    },
  },

  cleanUrls: true,
})
