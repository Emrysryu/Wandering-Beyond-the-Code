# Obsidian 与 GitHub 使用说明

这个仓库可以直接作为 Obsidian vault 使用。Obsidian 负责阅读、编辑和双链，GitHub 负责版本记录、远端备份和跨设备同步。

## 推荐设置

在 Obsidian 中打开这个目录：

```text
/Users/davidryu/Wandering-Beyond-the-Code/Wandering-Beyond-the-Code
```

附件设置：

```text
Files and links -> Default location for new attachments -> In the folder specified below
Attachment folder path -> 附件
```

## Git 同步

安装社区插件：

```text
Obsidian Git
```

安装路径：

```text
Settings -> Community plugins -> Turn on community plugins
Browse -> 搜索 Obsidian Git -> Install -> Enable
```

推荐配置：

```text
Auto pull interval: 10
Auto commit-and-sync interval: 10 或 30
Commit message: vault backup: {{date}}
Pull updates on startup: on
Push on backup: on
```

如果 Obsidian Git 设置项名称略有差异，按这个意思配置即可：

- 启动时自动 pull
- 定时自动 commit-and-sync
- 同步时 push 到远端
- commit message 使用日期，方便回滚

多设备使用时，先 pull 再编辑；如果出现冲突，不要直接覆盖，先保留两边版本再合并。

## 已忽略的本地状态

`.gitignore` 已忽略以下 Obsidian 本地状态：

```text
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/cache/
.trash/
```

这些文件主要记录窗口布局、临时缓存和废纸篓，不适合作为长期资料同步。
