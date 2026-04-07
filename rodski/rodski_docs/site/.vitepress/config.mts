import { defineConfig } from 'vitepress'
import { resolve } from 'path'

export default defineConfig({
  srcDir: '../../docs',
  outDir: '../dist',
  cacheDir: './cache',

  vite: {
    resolve: {
      alias: {
        'vue': resolve(__dirname, '../node_modules/vue'),
        'vue/server-renderer': resolve(__dirname, '../node_modules/vue/server-renderer'),
        '@vue/devtools-api': resolve(__dirname, '../node_modules/@vue/devtools-api'),
      },
    },
  },

  lang: 'zh-CN',
  title: 'RodSki 文档',
  description: 'RodSki 关键字驱动测试框架文档',

  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '指南', link: '/ARCHITECTURE' },
      {
        text: '参考',
        items: [
          { text: '关键字参考', link: '/SKILL_REFERENCE' },
          { text: 'API 参考', link: '/API_REFERENCE' },
        ],
      },
    ],

    sidebar: {
      '/': [
        {
          text: '入门',
          items: [
            { text: '文档首页', link: '/' },
            { text: '架构概览', link: '/ARCHITECTURE' },
          ],
        },
        {
          text: '核心设计',
          items: [
            { text: '核心设计约束', link: '/CORE_DESIGN_CONSTRAINTS' },
            { text: '数据文件组织', link: '/DATA_FILE_ORGANIZATION' },
          ],
        },
        {
          text: '编写指南',
          items: [
            { text: '测试用例编写指南', link: '/TEST_CASE_WRITING_GUIDE' },
            { text: 'JSON 支持', link: '/json_support_design' },
          ],
        },
        {
          text: '参考',
          items: [
            { text: '关键字参考', link: '/SKILL_REFERENCE' },
            { text: 'API 参考', link: '/API_REFERENCE' },
            { text: '数据库驱动', link: '/DB_DRIVER_SUPPORT' },
            { text: '视觉定位', link: '/VISION_LOCATION' },
          ],
        },
        {
          text: '集成',
          items: [
            { text: 'Agent 集成', link: '/AGENT_INTEGRATION' },
          ],
        },
      ],
    },

    search: {
      provider: 'local',
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/rodski' },
    ],
  },

  markdown: {
    lineNumbers: true,
  },
})
