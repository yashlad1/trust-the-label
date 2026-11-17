#!/bin/zsh
# Run tooling for the harness (piece Y7). Always goes through dev/py.sh.
# Usage, from anywhere:
#   dev/run.sh dry <stage1|stage2|stage3> [extra inspect args]               free, mockllm/model
#   dev/run.sh smoke <glm|nemotron35|luna|haiku|gptoss> <stage> [extra args]       12 samples, PAID
#   dev/run.sh full <glm|nemotron35|luna|haiku|gptoss> <stage> <outfile> [extra args]   detached, prints model and PID, PAID
# smoke and full are paid: Yash runs them himself, with his go.
# --model is the GATE for stage2 and the AGENT for stage1 and stage3.
# stage3 has NO default gate: pass -T gate_model=openrouter/<id> -T gate_config=dev/models/<gate>.yaml, plus -T gate_effort=medium for glm/luna/haiku/gptoss/nemotron35, matching that gate's stage-2 flags.
# smoke stage2: --limit 12 = 12 gate decisions, i.e. about 2 stored calls x 7 conditions.
# dry always forces a mockllm gate for stage3 too, so a dry run can never reach a paid model.
# stage2 needs -T logs=<comma-separated stage-1 .eval paths>; stage3 takes -T gate_model/policy/label/name/warning.
# Logs go to logs/<stage> inside .code-yash.
cd "${0:A:h:h}" || exit 1
USAGE="usage: dev/run.sh dry <stage> [args] | smoke <glm|nemotron35|luna|haiku|gptoss> <stage> [args] | full <glm|nemotron35|luna|haiku|gptoss> <stage> <outfile> [args]  (stage: stage1|stage2|stage3)"
MODE=$1
case $MODE in
  dry) STAGE=$2; M=(--model mockllm/model); shift 2 2>/dev/null ;;
  smoke|full) MODEL=$2; STAGE=$3; shift 3 2>/dev/null
    case $MODEL in
      glm) M=(--model openrouter/z-ai/glm-5.3-flash --model-config dev/models/glm-5.3-flash.yaml --reasoning-effort medium) ;;
      nemotron35) M=(--model openrouter/nvidia/nemotron-3.5-super-vl --model-config dev/models/nemotron-3.5-super-vl.yaml --reasoning-effort medium) ;;
      luna) M=(--model openrouter/openai/gpt-6-luna --model-config dev/models/gpt-6-luna.yaml --reasoning-effort medium) ;;
      haiku) M=(--model openrouter/anthropic/claude-haiku-5.5 --model-config dev/models/haiku.yaml --reasoning-effort medium) ;;
      gptoss) M=(--model openrouter/openai/gpt-oss-120b --model-config dev/models/gpt-oss-120b.yaml --reasoning-effort medium) ;;
      *) echo $USAGE; exit 1 ;;
    esac ;;
  *) echo $USAGE; exit 1 ;;
esac
case $STAGE in stage1|stage2|stage3) ;; *) echo $USAGE; exit 1 ;; esac
RUN=(dev/py.sh inspect eval src/trustlabel/harness/tasks.py@$STAGE $M --log-dir logs/$STAGE
     --display none --max-connections 4 --attempt-timeout 180 --max-retries 10 --fail-on-error 0.05
     --log-model-api)  # every raw response kept: OpenRouter's billed usage.cost is the only price for our models
case $MODE in
  dry) $RUN "$@" -T gate_model=mockllm/model -T gate_config= -T gate_effort= ;;
  smoke) $RUN --limit 12 --epochs 1 "$@" ;;
  full) OUT=${1:?outfile}; shift
    perl -MPOSIX -e 'POSIX::setsid(); exec @ARGV' -- caffeinate -is $RUN "$@" > "$OUT" 2>&1 < /dev/null &
    echo "$MODEL $!" ;;
esac
