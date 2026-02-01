@echo off
chcp 65001 >nul
cd /d "d:\标书工作流"
echo 正在添加所有变更...
git add .
echo 正在提交（说明：docs: 添加 README 与近期更新）...
git commit -m "docs: 添加 README 与近期更新"
if errorlevel 1 (
  echo 没有新变更可提交，或提交失败。若已提交过，直接推送即可。
  goto push
)
:push
echo 正在推送到 GitHub...
git push
echo.
echo 完成。若需修改提交说明，可先运行: git commit --amend -m "你的说明"
pause
