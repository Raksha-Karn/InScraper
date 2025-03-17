import random

def rotate_user_agents():
    with open('user_agents.txt', 'r') as user_agents:
        user_agents_list = user_agents.readlines()
        user_agent = random.choice(user_agents_list).strip()
        print(f'Using user agent: {user_agent}')
        return user_agent