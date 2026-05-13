import json
import random
import nest_asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import requests
import re

nest_asyncio.apply()

TOKEN = "8652125406:AAHz3XQnWvt_RFnvi0WMF15AGiywMwopSjw"

requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=True")

def escape_markdown(text):
    return text.replace('*', '').replace('_', '').replace('`', '')

with open('telegram_bot_tasks.json', 'r', encoding='utf-8') as f:
    TASKS = json.load(f)

with open('ege_tasks_1.json', 'r', encoding='utf-8') as f:
    raw_ege_tasks_1_data = json.load(f)

bot_tasks_set_1 = []
for task_raw in raw_ege_tasks_1_data:
    q_text = task_raw['problem_text']
    ans_exp = task_raw['answer_explanation']

    ans_match = re.search(r'Ответ:\s*(\d+)', ans_exp, re.IGNORECASE)
    ans = ans_match.group(1).strip() if ans_match else ""

    if ans:
        bot_tasks_set_1.append({
            "id": task_raw['problem_number'],
            "text": escape_markdown(q_text),
            "answer": ans.lower()
        })

user_ans = {} # Stores {user_id: correct_answer}

async def send_random_task(update, context, set_name_display=None):
    uid = update.effective_user.id
    
    # Get the list of tasks available for the current session/user
    available_tasks = context.user_data.get('available_tasks')
    selected_task_type_key = context.user_data.get('selected_task_type_key')

    if not available_tasks:
        # This means no set has been chosen yet or all tasks in the chosen set have been exhausted
        if selected_task_type_key:
            # All tasks of this type have been exhausted
            exhaustion_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Да", callback_data='restart_tasks')],
                [InlineKeyboardButton("Нет", callback_data='back_to_main_menu')]
            ])
            await update.effective_message.reply_text(
                "Вы прорешали все задания этого типа! Хотите начать заново?",
                reply_markup=exhaustion_keyboard
            )
        else:
            # No task type selected initially or after returning to main menu
            await update.effective_message.reply_text("Пожалуйста, сначала выберите тип заданий с помощью /start.")
        return

    # Increment task counter for the user
    context.user_data['task_counter'] = context.user_data.get('task_counter', 0) + 1
    task_display_number = context.user_data['task_counter']

    # Choose a random task and remove it from the available list to prevent repetition
    t = random.choice(available_tasks)
    available_tasks.remove(t)

    user_ans[uid] = t['answer']
    prefix = f"Выбран {set_name_display}.\n\n" if set_name_display else ""
    await update.effective_message.reply_text(
        text=f"{prefix}📝 *Задание {task_display_number}*\n\n{t['text']}\n\n✏️ *Напиши ответ:*",
        parse_mode='Markdown'
    )

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("Орфография", callback_data='choose_set_1')],
        [InlineKeyboardButton("Паронимы", callback_data='choose_set_2')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Use update.effective_message for reply_text to work with both CommandHandler and CallbackQueryHandler
    await update.effective_message.reply_text("Выберите тип заданий:", reply_markup=reply_markup)

async def get_task(update, context):
    await send_random_task(update, context)


async def button_callback_handler(update, context):
    query = update.callback_query
    await query.answer() # Acknowledge the button press

    uid = update.effective_user.id # Use update.effective_user.id directly

    if query.data == 'choose_set_1':
        context.user_data['available_tasks'] = list(bot_tasks_set_1) # Create a copy for the session
        context.user_data['selected_task_type_key'] = 'set_1'
        context.user_data['task_counter'] = 0 # Reset counter
        await send_random_task(update, context, "Орфография") # Pass original update object
    elif query.data == 'choose_set_2':
        context.user_data['available_tasks'] = list(TASKS) # Create a copy for the session
        context.user_data['selected_task_type_key'] = 'set_2'
        context.user_data['task_counter'] = 0 # Reset counter
        await send_random_task(update, context, "Паронимы") # Pass original update object
    elif query.data == 'get_another_task':
        await send_random_task(update, context)
    elif query.data == 'back_to_main_menu':
        if 'available_tasks' in context.user_data:
            del context.user_data['available_tasks']
        if 'selected_task_type_key' in context.user_data:
            del context.user_data['selected_task_type_key']
        context.user_data['task_counter'] = 0 # Reset counter
        await start(update, context) # Re-call start to show menu again
    elif query.data == 'restart_tasks':
        selected_task_type_key = context.user_data.get('selected_task_type_key')
        if selected_task_type_key == 'set_1':
            context.user_data['available_tasks'] = list(bot_tasks_set_1)
            display_name = "Орфография"
        elif selected_task_type_key == 'set_2':
            context.user_data['available_tasks'] = list(TASKS)
            display_name = "Паронимы"
        else:
            await query.message.reply_text("Не удалось определить тип заданий для перезапуска.")
            return

        context.user_data['task_counter'] = 0 # Reset counter for a new 'session' of this type
        await query.message.reply_text(f"Начинаем заново! Выбран {display_name}.")
        await send_random_task(update, context, display_name)
    else:
        await query.message.reply_text("Неизвестный выбор.")


async def check(update, context):
    uid = update.effective_user.id
    if uid not in user_ans:
        await update.message.reply_text("Пожалуйста, сначала выберите набор заданий с помощью /start, затем получите задание.")
        return

    raw_user_input = update.message.text.lower().replace('ё', 'е').strip()
    
    want = user_ans[uid].lower().replace('ё', 'е').strip()

    # Normalize user's input based on whether the expected answer is purely numeric
    if want.isdigit():
        got = raw_user_input.replace(" ", "")
    else:
        got = " ".join(raw_user_input.split())
        # Ensure 'want' also has consistent space handling if it's not numeric
        want = " ".join(want.split())

    feedback_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Ещё!", callback_data='get_another_task')],
        [InlineKeyboardButton("К выбору типа", callback_data='back_to_main_menu')]
    ])

    if got == want:
        await update.message.reply_text("Правильно!", reply_markup=feedback_keyboard)
    else:
        await update.message.reply_text(f"Неправильно. Правильный ответ: *{want}*", parse_mode='Markdown', reply_markup=feedback_keyboard)

    del user_ans[uid]


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("task", get_task))
app.add_handler(CallbackQueryHandler(button_callback_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check))

print("Бот запущен")
app.run_polling(drop_pending_updates=True)
