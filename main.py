# 当前为多轮agent
from agent.core.loop import EcommerceAgent

agent = EcommerceAgent()

def main():
    while True:
        user_input = input("用户：")
        if user_input == "exit":
            break
        result = agent.run(user_input)
        print("AI：", result)

if __name__ == '__main__':
    main()