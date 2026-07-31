#!/usr/bin/env bash
# GLM 工人：用 Claude Code 无头模式执行单个开发任务，模型走火山方舟 Coding Plan（GLM-5.2）。
# 这样编码消耗方舟套餐额度，而不是 Anthropic token；规划与审查仍由 Claude 会话完成。
#
# 用法:
#   scripts/glm/run-task.sh <task-file.md> [workdir]
#
# 前置:
#   - ~/.claude/secrets/ark.env 内含 ARK_API_KEY（不入库）
#   - 已安装 claude CLI（Claude Code）
#
# 环境变量开关:
#   GLM_MODEL      默认 glm-5.2；长上下文任务可用 glm-5.2[1m]
#   GLM_MAX_TURNS  默认 60
#   GLM_YOLO=1     改用 --dangerously-skip-permissions（仅限隔离 worktree 内使用）
#
# 注意: Base URL 必须是 api/coding（消耗套餐额度）；api/v3 会按量另计费。
set -euo pipefail

TASK_FILE="${1:?用法: run-task.sh <task-file.md> [workdir]}"
WORKDIR="${2:-$(git rev-parse --show-toplevel)}"
source "$HOME/.claude/secrets/ark.env"

MODEL="${GLM_MODEL:-glm-5.2}"
MAX_TURNS="${GLM_MAX_TURNS:-60}"
LOG_DIR="$WORKDIR/.glm-logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(basename "$TASK_FILE" .md)-$(date +%Y%m%d-%H%M%S).json"

PERM_ARGS=(--permission-mode acceptEdits --allowedTools "Bash(env:*),Bash(python:*),Bash(python3:*),Bash(pytest:*),Bash(pip:*),Bash(uv:*),Bash(/Users/rick/ZCodeProject/.venv/bin/python:*),Bash(/Users/rick/ZCodeProject/.venv/bin/pytest:*),Bash(npm:*),Bash(npx:*),Bash(node:*),Bash(ls:*),Bash(cat:*),Bash(head:*),Bash(tail:*),Bash(wc:*),Bash(grep:*),Bash(find:*),Bash(echo:*),Bash(mkdir:*),Bash(chmod +x:*),Bash(cd:*),Bash(git status:*),Bash(git diff:*),Bash(git log:*),Bash(git rev-parse:*),Bash(curl -sS http://127.0.0.1:*)")
if [[ "${GLM_YOLO:-0}" == "1" ]]; then
  PERM_ARGS=(--dangerously-skip-permissions)
fi

ROLE_PREAMBLE='【角色声明·最高优先级】你是本任务的执行工人（coding worker），不是规划者。亲自读代码、亲自编辑文件、亲自运行验收命令。严格禁止：再分发任务、调用 scripts/glm/run-task.sh、启动任何嵌套 agent/工人、修改 scripts/glm/tasks/ 下的任务书、用"决策请求/请示"替代动手实现。仓库文档中"编码由 GLM 工人执行、Claude 只做规划审查"描述的流水线里，你就是那个 GLM 工人本人——现在开始动手。唯一合法产出=对目标文件的代码改动+最终文字报告。以下是任务书：'

run_worker() {
  # $1 = backend: ark | anthropic; $2 = model
  local backend="$1" model="$2"
  if [[ "$backend" == "anthropic" ]]; then
    # Rick 2026-07-11 指令: 方舟 5 小时配额打满后切 Anthropic 模型(opus/sonnet,按任务复杂度)
    env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT \
      claude -p "$ROLE_PREAMBLE
$(cat "$TASK_FILE")" \
        --model "$model" \
        "${PERM_ARGS[@]}" \
        --max-turns "$MAX_TURNS" \
        --output-format json | tee "$LOG"
  else
    env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT \
      ANTHROPIC_BASE_URL="https://ark.cn-beijing.volces.com/api/coding" \
      ANTHROPIC_AUTH_TOKEN="$ARK_API_KEY" \
      ANTHROPIC_MODEL="$model" \
      ANTHROPIC_DEFAULT_HAIKU_MODEL="$model" \
      ANTHROPIC_DEFAULT_SONNET_MODEL="$model" \
      ANTHROPIC_DEFAULT_OPUS_MODEL="$model" \
      CLAUDE_CODE_SUBAGENT_MODEL="$model" \
      claude -p "$ROLE_PREAMBLE
$(cat "$TASK_FILE")" \
        --model "$model" \
        "${PERM_ARGS[@]}" \
        --max-turns "$MAX_TURNS" \
        --output-format json | tee "$LOG"
  fi
}

cd "$WORKDIR"
if [[ "$MODEL" == "opus" || "$MODEL" == "sonnet" ]]; then
  run_worker anthropic "$MODEL"
else
  run_worker ark "$MODEL"
  # 方舟 5 小时配额打满 -> 自动降级 Anthropic 重跑一次(默认 opus,可用 GLM_FALLBACK_MODEL=sonnet 指定)
  if grep -q "exceeded the 5-hour usage quota" "$LOG" 2>/dev/null; then
    FB="${GLM_FALLBACK_MODEL:-opus}"
    echo ""
    echo "== 方舟配额打满,按既定策略降级 Anthropic($FB) 重跑 =="
    LOG="$LOG_DIR/$(basename "$TASK_FILE" .md)-fb-$(date +%Y%m%d-%H%M%S).json"
    run_worker anthropic "$FB"
  fi
fi

echo ""
echo "== 完成。日志: $LOG"
echo "== 审查: git -C $WORKDIR diff --stat"
