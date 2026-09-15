# 当前为多轮agent
from agent.core.loop import EcommerceAgent

agent = EcommerceAgent()

def main():
    while True:
        user_input = input("用户：")
        if user_input == "exit":
            break
        result = agent.run(user_input)
        for line in result.replies:
            print("AI：", line)
        u = result.usage
        print(f"  · 本轮 {u['llm_calls']} 次调用 | "
              f"tokens 输入 {u['prompt_tokens']} / 输出 {u['completion_tokens']}（缓存命中 {u['cached_tokens']}） | "
              f"耗时 {u['latency_ms'] / 1000:.1f}s")

if __name__ == '__main__':
    main()