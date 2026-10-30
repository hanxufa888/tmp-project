
验证 mcp, speck2model 功能


KGA_TEST_FILES  这个目录下面是我打算用于生成harbor 测试集的材料；
KGA_TEST_FILES/prod-dev1-skl-speccheck 这个文件暂时忽略；

测试目标是打算生成一个dokcer 容器，里面安装claude code 这个agent,
然后我打算给claude code 配置一个mcp 连接；
然后提问KGA_TEST_FILES/insruction.md 里面的问题，期待能够得到一个答案；

那么按照 harbor 的测试集结构，
environment/Dockerfile 里面安装claude code agent, 并且配置mcp连接；
Dockerfile 可以参考 examples/tasks/hello-world/environment/Dockerfile，
这个里面已经有了claude code 安装的注意是事项，你只需要考虑mcp 如何在claude code 安装之后配置好就可以了；

然后关于solution, 这个我还真不清楚要怎么写，或者不写，或者写个默认的内容可以吗？
然后task.toml 我也不清楚里面是什么样的规范；可以参考 examples/tasks/hello-world/task.toml；
最后我这个提问的任务得到的答案会被保存到哪里也是个问题，我期待能保存在容器外面的目录中，不知道harbor的测试集可以
实现这个需求吗？

请梳理我的需求，然后思考我提到的问题可以怎么处理？
帮我生成测试case 到examples/tasks/KGA_mcp


172.30.251.179 是我在hostname -I 得到的IP 地址，用来替换上面提到的127.0.0.1 这个IP 可以吗？
如果可以，帮我生成测试case 到目录examples/tasks/KGA_mcp 下面


uv run --with harbor-atif2otel harbor run \
  -p ./examples/tasks/KGA_mcp \
  -a claude-code \
  --sm \
  -m github_copilot/gpt-6.1-sol \
  -e docker \
  -n 1 \
  --ae ANTHROPIC_AUTH_TOKEN="sk-123456qweasd" \
  --ae ANTHROPIC_BASE_URL=http://172.23.0.1:4001 \
  --ae ANTHROPIC_DEFAULT_HAIKU_MODEL=github_copilot/gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_SONNET_MODEL=github_copilot/gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_OPUS_MODEL=github_copilot/gpt-6-astra \
  --ae KGA_MCP_AUTHORIZATION="Bearer mkb_vemaa6GG-4e7aDzzRB7PAT4BWsLOHcVNUVtRSn8cnVw" \
  --ae API_TIMEOUT_MS=3000000 \
  --plugin atif2otel \
  --pk endpoint=http://localhost:5100 \
  --pk experiment_name=harbor-test-traces \
  --pk output_dir=./otel-traces \
  --pk encoding=json




 uv run --with harbor-atif2otel harbor run \
  -p ./examples/tasks/KGA_mcp\
  -a claude-code \
  --sm \
  -m gpt-6.1-sol \
  -e docker \
  -n 1 \
  --ae ANTHROPIC_AUTH_TOKEN="sk-123456qweasd" \
  --ae ANTHROPIC_BASE_URL=http://172.30.251.179:4002 \
  --ae ANTHROPIC_DEFAULT_HAIKU_MODEL=gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_SONNET_MODEL=gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_OPUS_MODEL=gpt-6.1-sol \
  --ae KGA_MCP_AUTHORIZATION="Bearer mkb_vCb1IOJnXo8VTy81gyCNCcBhDG8WHwLgOeDW6Ep3-zg" \
  --ae API_TIMEOUT_MS=3000000 \
  --plugin atif2otel \
  --pk endpoint=http://localhost:5100 \
  --pk experiment_name=harbor-test-traces \
  --pk output_dir=./otel-traces \
  --pk encoding=json
 

KGA_TEST_FILES  这个目录下面有一个 KGA_TEST_FILES/insruction.md 和KGA_TEST_FILES/MET-C_SLIP-CSTD-0-01-B-C0.xlsm
我打算使用刚刚生成的最新的镜像作为基础的镜像；
然后参考 examples/tasks/KGA_mcp 准备两个测试case;
分别测试mcp 的功能；以及最新镜像里面skill 中将文件转为markdown 的功能；

请你帮我完成在 examples/tasks/KGA_mcp_test 及 examples/tasks/KGA_file2markdown 下面
然后参考命令：
 uv run --with harbor-atif2otel harbor run \
  -p ./examples/tasks/KGA_mcp\
  -a claude-code \
  --sm \
  -m gpt-6.1-sol \
  -e docker \
  -n 1 \
  --ae ANTHROPIC_AUTH_TOKEN="sk-123456qweasd" \
  --ae ANTHROPIC_BASE_URL=http://172.30.251.179:4002 \
  --ae ANTHROPIC_DEFAULT_HAIKU_MODEL=gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_SONNET_MODEL=gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_OPUS_MODEL=gpt-6.1-sol \
  --ae KGA_MCP_AUTHORIZATION="Bearer mkb_vCb1IOJnXo8VTy81gyCNCcBhDG8WHwLgOeDW6Ep3-zg" \
  --ae API_TIMEOUT_MS=3000000 \
  --plugin atif2otel \
  --pk endpoint=http://localhost:5100 \
  --pk experiment_name=harbor-test-traces \
  --pk output_dir=./otel-traces \
  --pk encoding=json
帮我完成功能的测试；要求主要的结果要输出到结果目录下面




 uv run --with harbor-atif2otel harbor run \
  -p ./examples/tasks/MET-C_STEER-CSTD \
  -a claude-code \
  --sm \
  -m gpt-6.1-sol \
  -e docker \
  -n 1 \
  --ae ANTHROPIC_AUTH_TOKEN="sk-123456qweasd" \
  --ae ANTHROPIC_BASE_URL=http://172.30.251.179:4001 \
  --ae ANTHROPIC_DEFAULT_HAIKU_MODEL=gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_SONNET_MODEL=gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_OPUS_MODEL=gpt-6.1-sol \
  --ae KGA_MCP_AUTHORIZATION="Bearer mkb_vCb1IOJnXo8VTy81gyCNCcBhDG8WHwLgOeDW6Ep3-zg" \
  --ae API_TIMEOUT_MS=3000000 \
  --plugin atif2otel \
  --pk endpoint=http://localhost:5100 \
  --pk experiment_name=harbor-test-traces \
  --pk output_dir=./otel-traces \
  --pk encoding=json
 


 uv run --with harbor-atif2otel harbor run \
  -p ./examples/tasks/MET-C_STEER-CSTD \
  -a claude-code \
  --sm \
  -m github_copilot/gpt-6.1-sol \
  -e docker \
  -n 1 \
  --ae ANTHROPIC_AUTH_TOKEN="sk-123456qweasd" \
  --ae ANTHROPIC_BASE_URL=http://172.23.0.1:4001 \
  --ae ANTHROPIC_DEFAULT_HAIKU_MODEL=github_copilot/gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_SONNET_MODEL=github_copilot/gpt-6.1-sol \
  --ae ANTHROPIC_DEFAULT_OPUS_MODEL=github_copilot/gpt-6-astra \
  --ae KGA_MCP_AUTHORIZATION="Bearer mkb_vCb1IOJnXo8VTy81gyCNCcBhDG8WHwLgOeDW6Ep3-zg" \
  --ae API_TIMEOUT_MS=3000000 \
  --plugin atif2otel \
  --pk endpoint=http://localhost:5100 \
  --pk experiment_name=harbor-test-traces \
  --pk output_dir=./otel-traces \
  --pk encoding=json
 
