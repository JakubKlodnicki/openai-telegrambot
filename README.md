# openai-telegrambot
OpenAI bot on telegram

1. Create venv
2. pip install -r requirements.txt (install require modules)
3. In .env put your api`s keys
4. In app.py in allowed_users put your id user from telegram
5. python app.py (To run app)

If u get problem with migrate run in venv "openai migrate"

Language of output texts: PL-pl

In next update i will add other lanuages

## Functions
- Select GPT versions (gpt3.5 turbo, gpt4.0, gpt4o *Dall-e dont work*)
- Analize text files ('.py', '.txt', '.js', '.html', '.css', '.json', '.xml', '.sql', '.md', '.c', '.cpp', '.java', '.rb', '.php', '.sh', '.bat', '.ini', '.yml', '.yaml', '.r', '.pl')
- Analize text from images (But to update, dont work well)
- Generation images (Only work with english descriptions)