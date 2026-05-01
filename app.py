import logging
import json
import os
import uuid
import random
import string
import re
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient
from dotenv import load_dotenv

# --- تحميل الإعدادات الآمنة من ملف .env ---
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')

# --- الإعدادات الأساسية ---
MY_ID = 7843480484
BASE_ALLOWED_USERS = [MY_ID, 5633714544, 5606716555, 5459263268, 8574308047, 6797598284, 6811694086, 5591105371, 6101627394, 5456916922, 1429658161, 8013560935]
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)

# --- الاتصال بقاعدة بيانات MongoDB ---
try:
    client = MongoClient(MONGO_URI)
    db = client['telegram_bot_db']
    app_data = db['app_data'] # الكولكشن اللي هنحفظ فيه كل حاجة
    client.admin.command('ping')
    logging.info("✅ تم الاتصال بقاعدة بيانات MongoDB بنجاح!")
except Exception as e:
    logging.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")

# --- دوال التعامل مع قاعدة البيانات (تم التعديل لتعمل مع MongoDB) ---
def load_data(doc_id, default):
    try:
        doc = app_data.find_one({"_id": doc_id})
        if doc:
            return doc.get("data", default)
        else:
            app_data.insert_one({"_id": doc_id, "data": default})
            return default
    except Exception as e:
        logging.error(f"Error loading {doc_id}: {e}")
        return default

def save_data(doc_id, data):
    try:
        app_data.update_one({"_id": doc_id}, {"$set": {"data": data}}, upsert=True)
    except Exception as e:
        logging.error(f"Error saving {doc_id}: {e}")

# --- جلب البيانات عند بدء التشغيل ---
default_content = {
    "subjects": {
        "nurs2": "أساسيات تمريض 2 نظري",
        "health_edu": "تثقيف صحي",
        "quality": "أساسيات جودة",
        "nurs_pr": "أساسيات تمريض عملي",
        "eval_pr": "تقييم صحي عملي",
        "comm": "مهارات تواصل",
        "life": "نمط حياة صحي"
    },
    "categories": {
        "nurs2": {"lect": "📝 شرح", "ques": "❓ أسئلة", "vid": "🎥 فيديوهات", "voice": "🎙️ ريكوردات"},
        "health_edu": {"lect": "📝 شرح", "ques": "❓ أسئلة"},
        "quality": {"lect": "📝 شرح", "ques": "❓ أسئلة"},
        "nurs_pr": {"lect": "📝 شرح"},
        "eval_pr": {"lect": "📝 شرح"},
        "comm": {"lect": "📝 شرح", "ques": "❓ أسئلة"},
        "life": {"lect": "📝 شرح", "ques": "❓ أسئلة"}
    },
    "files": {
        'life_lect_chronic': ('BQACAgQAAxkBAAICrmndJJpssXr4Csd1tLauJLyjDunWAAKmGgACDQHpUh1thfy0Fin_OwQ', 'Chronic Diseases (شرح)', 'document'),
        'life_lect_diabetes': ('BQACAgQAAxkBAAICr2ndJJrAKVB8_YbrxxHOAAGEdqnCuQACpxoAAg0B6VJbXfLX531adTsE', 'Diabetes Mellitus (شرح)', 'document'),
        'life_lect_promo': ('BQACAgQAAxkBAAICsGndJJqxnCjAweAWGI-s68aOcKIUAAKoGgACDQHpUs3VXvjEPKZSOwQ', 'Health Promotion (شرح)', 'document'),
        'life_lect_cancer': ('BQACAgQAAxkBAAICsWndJJpk2B4fo8JcoevhJ96JyO5NAAKqGgACDQHpUsreaU_ck_nKOwQ', 'Cancer & CVD Lifestyle (شرح)', 'document'),
        'life_lect_hyper': ('BQACAgQAAxkBAAICsmndJJrtD6FkQpABwZcdxtPydEFWAAKrGgACDQHpUlVBiiYnd-NwOwQ', 'Hypertension (شرح)', 'document'),
        'life_lect_overview': ('BQACAgQAAxkBAAICs2ndJJoykMtxwQFBw3YL5S4rTV1IAAKsGgACDQHpUuDN65PqEiKYOwQ', 'Overview for Healthy Lifestyle (شرح)', 'document'),
        'life_lect_role': ('BQACAgQAAxkBAAICtGndJJoJz9_88QY8G7dHhTb794GEAAKtGgACDQHpUjP59Qn9P0MlOwQ', 'Role of Community Nurse (شرح)', 'document'),
        'life_ques_chronic': ('BQACAgQAAxkBAAICvGndJRmBnh4qkiHka85P23GRS0ryAAKuGgACDQHpUp51QIDiAAG0vTsE', 'Chronic Diseases (أسئلة)', 'document'),
        'life_ques_diabetes': ('BQACAgQAAxkBAAICvWndJRnoEEEtp9gH_XhQNUW4xiFeAAKvGgACDQHpUtIcZzM0zUn1OwQ', 'Diabetes Mellitus (أسئلة)', 'document'),
        'life_ques_promo': ('BQACAgQAAxkBAAICvmndJRn8OZ9mgwVK7Yy7gv-NrxOLAAKwGgACDQHpUgEMswl9Tpp7OwQ', 'Health Promotion (أسئلة)', 'document'),
        'life_ques_cancer': ('BQACAgQAAxkBAAICv2ndJRmi9-CibXPoxGjrF1vx9QvDAAKxGgACDQHpUjxUQ7laN_9POwQ', 'Cancer & CVD Lifestyle (أسئلة)', 'document'),
        'life_ques_hyper': ('BQACAgQAAxkBAAICwGndJRkMFgdx2WmSkde5bc2hgV9-AAKyGgACDQHpUm9QIzXg4chKOwQ', 'Hypertension (أسئلة)', 'document'),
        'life_ques_overview': ('BQACAgQAAxkBAAICwWndJRlXjjpU9KLBtylfFWROEhoxAAKzGgACDQHpUlL0eZIU-mltOwQ', 'Overview for Healthy Lifestyle (أسئلة)', 'document'),
        'life_ques_role': ('BQACAgQAAxkBAAICwmndJRmd03qqB0kUlI-x5wbwQwwnAAK0GgACDQHpUkZAmF0FRVILOwQ', 'Role of Community Nurse (أسئلة)', 'document'),
        'comm_lect_1': ('BQACAgQAAxkBAAICqGndIPawM4nOEHpvz_c-dTyG0ZJIAAKiGgACDQHpUs8zfuj4hFvnOwQ', 'مهارات تواصل - شرح 1', 'document'),
        'comm_ques_1': ('BQACAgQAAxkBAAICrGndItuhRymMkfsAAWZQVgAB_JzJaDYAAqQaAAINAelS5CURjeuH2KE7BA', 'مهارات تواصل - أسئلة 1', 'document'),
        'eval_pr_lect_ear': ('BQACAgQAAxkBAAICkmndIAFHsniNsohV-dgcV2DGfmWIAAKWGgACDQHpUiMF6EFz3ilUOwQ', 'Ear Assessment', 'document'),
        'eval_pr_lect_git': ('BQACAgQAAxkBAAICk2ndIAF_CnHvk15fl3DfucVysWRGAAKXGgACDQHpUixbTxWWpBSJOwQ', 'Gastrointestinal System', 'document'),
        'eval_pr_lect_heart': ('BQACAgQAAxkBAAIClGndIAH_QHpHHogAAfZOnQJwiVWihwACmBoAAg0B6VKIwqcRytV-9zsE', 'Heart and Neck Vessels', 'document'),
        'eval_pr_lect_peri': ('BQACAgQAAxkBAAIClWndIAG0z44zyQ91Kea9PeKjWOk7AAKZGgACDQHpUjAn7XmQ72FOOwQ', 'Peripheral Vascular', 'document'),
        'eval_pr_lect_thorax': ('BQACAgQAAxkBAAIClmndIAErD4fnkIJxepcwRxYZiHlBAAKaGgACDQHpUnZTKAK4AAGSdTsE', 'Thorax and Lungs', 'document'),
        'eval_pr_lect_eye': ('BQACAgQAAxkBAAICl2ndIAHJOai02assOfdjByhzPgHrAAKbGgACDQHpUjicIIjOQNuxOwQ', 'Eye Assessment', 'document'),
        'eval_pr_lect_head': ('BQACAgQAAxkBAAICmGndIAFbuI9WdzCgUlPe-W213v7-AAKcGgACDQHpUp6dRQtyiLtUOwQ', 'Head, Face and Neck', 'document'),
        'eval_pr_lect_integ': ('BQACAgQAAxkBAAICmWndIAHtay74q-jnCK2SG9cZMfmVAAKdGgACDQHpUgRB_45IM1yLOwQ', 'Integumentary System', 'document'),
        'eval_pr_lect_nose': ('BQACAgQAAxkBAAICmmndIAGiQ9scHlZ-4RkOQFsMDIGrAAKeGgACDQHpUpEAAQO3CnN-rjsE', 'Nose Sinus Mouth Throat', 'document'),
        'eval_pr_lect_visual': ('BQACAgQAAxkBAAICm2ndIAGxvAUZVi0H0c_P-KeRpt3tAAKfGgACDQHpUldNBMGYmb9_OwQ', 'Visual Acuity', 'document'),
        'nurs2_lect_bowel': ('BQACAgQAAxkBAAICCWndGboCizFLgXvmz-oIS4lPfr-pAAJWGgACDQHpUj-dOvT4SvYWOwQ', 'Bowel Elimination (شرح)', 'document'),
        'nurs2_lect_diag': ('BQACAgQAAxkBAAICCmndGboPKohO6mIj5NoTCBAHtht8AAJXGgACDQHpUlnxuf_bAmznOwQ', 'Diagnostic Test (شرح)', 'document'),
        'nurs2_lect_fluid': ('BQACAgQAAxkBAAICC2ndGbq-LfIQkbQUXp21q2U6mVhaAAJYGgACDQHpUoMAAW3u5uoM9zsE', 'Fluid Balance (شرح)', 'document'),
        'nurs2_lect_oxy': ('BQACAgQAAxkBAAICDGndGbpR0D-L7_LUl_5U1ZbrPg5IAAJZGgACDQHpUoHS5Eb9HLPKOwQ', 'Oxygen Therapy (شرح)', 'document'),
        'nurs2_lect_med': ('BQACAgQAAxkBAAICDWndGborCbYCk5eKn6C_PWVcYsVIAAJaGgACDQHpUlt2KEdHMb3pOwQ', 'Medication Administration (شرح)', 'document'),
        'nurs2_lect_proc': ('BQACAgQAAxkBAAICDmndGbpKnPFsX5OyP-HUYyKHngFIAAJbGgACDQHpUhz56hqny3GIOwQ', 'Nursing Process (شرح)', 'document'),
        'nurs2_lect_skin': ('BQACAgQAAxkBAAICD2ndGbrsJypS0AgIEmeUQbjOWcw4AAJcGgACDQHpUumOWBsZ6tFNOwQ', 'Skin Integrity (شرح)', 'document'),
        'nurs2_lect_uri': ('BQACAgQAAxkBAAICEGndGbqe2zWLLrZyvdTmKbCYPwtGAAJdGgACDQHpUi1EHWq6gWaJOwQ', 'Urinary Lecture (شرح)', 'document'),
        'nurs2_ques_bowel': ('BQACAgQAAxkBAAICHmndG5_xe9UJHLz_2yWlEg-kkElGAAJeGgACDQHpUtzXHdIlFwmbOwQ', 'Bowel Elimination (أسئلة)', 'document'),
        'nurs2_ques_diag': ('BQACAgQAAxkBAAICH2ndG5-HITXmNfeV0xmpD4Rp55r7AAJfGgACDQHpUljAHCJnrN8eOwQ', 'Diagnostic Test (أسئلة)', 'document'),
        'nurs2_ques_fluid': ('BQACAgQAAxkBAAICIGndG58SvrPs3jkW7Wr15_hpDyK6AAJgGgACDQHpUtT-W8kMxU7hOwQ', 'Fluid Balance (أسئلة)', 'document'),
        'nurs2_ques_med': ('BQACAgQAAxkBAAICIWndG5_1aDUzYxnWbDPv5ZPwZbZGAAJhGgACDQHpUpLU8nxOs0ifOwQ', 'Medication Administration (أسئلة)', 'document'),
        'nurs2_ques_proc': ('BQACAgQAAxkBAAICImndG5_dWHnZxZ9SlLZR2srC1-W9AAJiGgACDQHpUkikQvduY5Q0OwQ', 'Nursing Process (أسئلة)', 'document'),
        'nurs2_ques_oxy': ('BQACAgQAAxkBAAICI2ndG5-KYulZ7db05f6QbpU0ohPzAAJjGgACDQHpUlPvaCFH5yQrOwQ', 'Oxygen Therapy (أسئلة)', 'document'),
        'nurs2_ques_skin': ('BQACAgQAAxkBAAICJGndG5_6sfHlf8Kh-M5X4gfTmVU3AAJkGgACDQHpUgM4XlD8vRmVOwQ', 'Skin Integrity (أسئلة)', 'document'),
        'nurs2_ques_uri': ('BQACAgQAAxkBAAICJWndG5-2UtH4SRMolYCW7NAfPwziAAJlGgACDQHpUtel1S3Nt923OwQ', 'Urinary (أسئلة)', 'document'),
        'quality_lect_acc': ('BQACAgQAAxkBAAICNWndHPlqSfJZdS8jkg_X-_2v6g7IAAJnGgACDQHpUkVezliHJjguOwQ', 'Accreditation (شرح)', 'document'),
        'quality_lect_change': ('BQACAgQAAxkBAAICNmndHPmtXkieUTEeXoxpDJZ3SL7dAAJoGgACDQHpUj3dWI6cCmkhOwQ', 'Managing Change (شرح)', 'document'),
        'quality_lect_super': ('BQACAgQAAxkBAAICN2ndHPm3aSfws3R7OYp_ibpzpO2MAAJpGgACDQHpUjZC8sIfJEYYOwQ', 'Monitoring and Supervision (شرح)', 'document'),
        'quality_lect_rights': ('BQACAgQAAxkBAAICOGndHPnfIFjvGga8UVUBhBn4a8d6AAJqGgACDQHpUhA6jkPOZNnfOwQ', 'Patient Rights (شرح)', 'document'),
        'quality_lect_safety': ('BQACAgQAAxkBAAICOWndHPkOi7sd8M9pJ8Q-HxQhr4LpAAJrGgACDQHpUoU-E_hxBoQzOwQ', 'Patient Safety (شرح)', 'document'),
        'quality_lect_ctrl': ('BQACAgQAAxkBAAICOmndHPmiNp-IvrnE1XKdOpqvPFqpAAJsGgACDQHpUkAEuUGWpcpzOwQ', 'Quality Control (شرح)', 'document'),
        'quality_lect_impr': ('BQACAgQAAxkBAAICO2ndHPmSbY0VaKl3yLY6i1SE7QgSAAJtGgACDQHpUoXPwx3IESK_OwQ', 'Quality Improvement (شرح)', 'document'),
        'quality_lect_life': ('BQACAgQAAxkBAAICPGndHPlU9CoCLgPbenekvQ6x81CMAAJuGgACDQHpUuh1ctvHZkRxOwQ', 'Quality of Work Life (شرح)', 'document'),
        'quality_lect_std': ('BQACAgQAAxkBAAICPWndHPlq6JNmnmCnwSzYeVDYDmp8AAJvGgACDQHpUlC1DJOLm3TbOwQ', 'Standards (شرح)', 'document'),
        'quality_lect_qa': ('BQACAgQAAxkBAAICPmndHPl3NbDa4ClQl2JTi1B2OgWcAAJwGgACDQHpUsIOIoEfQ8OwQ', 'Concept of Quality Assurance (شرح)', 'document'),
        'quality_lect_conc': ('BQACAgQAAxkBAAICSWndHQVtQhnYGlA8lLpgZaefTyYZAAJxGgACDQHpUqaVx8h9v2MVOwQ', 'Concepts of Quality (شرح)', 'document'),
        'quality_lect_tqm': ('BQACAgQAAxkBAAICSmndHQUKIN3WhL1rknlNz13BtvmDAAJyGgACDQHpUveLEJ-dPiSFOwQ', 'Total Quality Management (شرح)', 'document'),
        'quality_ques_acc': ('BQACAgQAAxkBAAICT2ndHYwXoV8Xux_P7Y4HH1k9bRKBAAJzGgACDQHpUhuw-msQ_JKvOwQ', 'Accreditation (أسئلة)', 'document'),
        'quality_ques_change': ('BQACAgQAAxkBAAICUGndHYxYmR6cC5HhIDfNWkMafTKzAAJ0GgACDQHpUj67XTlqmibjOwQ', 'Managing Change (أسئلة)', 'document'),
        'quality_ques_super': ('BQACAgQAAxkBAAICUWndHYxFIXSrp3QNKBNJIwLmwMUVAAJ1GgACDQHpUmxD7KrP6Y9AOwQ', 'Monitoring and Supervision (أسئلة)', 'document'),
        'quality_ques_rights': ('BQACAgQAAxkBAAICUmndHYwz7bicvqK9jvBH3cJ_n-nDAAJ2GgACDQHpUmc6nW9npQauOwQ', 'Patient Rights (أسئلة)', 'document'),
        'quality_ques_safety': ('BQACAgQAAxkBAAICU2ndHYzvDObCPspdtREUFIwrjYlKAAJ3GgACDQHpUk3Ht66e8OoaOwQ', 'Patient Safety (أسئلة)', 'document'),
        'quality_ques_ctrl': ('BQACAgQAAxkBAAICVGndHYwpUXsrOOGXaJWNlv0YXtDIAAJ4GgACDQHpUtiJz2jzWkwwOwQ', 'Quality Control (أسئلة)', 'document'),
        'quality_ques_impr': ('BQACAgQAAxkBAAICVWndHYx-kg_GFUXPsWUiAfbwa-N8AAJ5GgACDQHpUiPTBdrrGcIUOwQ', 'Quality Improvement (أسئلة)', 'document'),
        'quality_ques_life': ('BQACAgQAAxkBAAICVmndHYyWDI-Bo6Rv6rxxZPfncuHuAAJ6GgACDQHpUqTD7KNJq-SZOwQ', 'Quality of Work Life (أسئلة)', 'document'),
        'quality_ques_std': ('BQACAgQAAxkBAAICV2ndHYygIyirNxGA6-07CPLCjn6KAAJ7GgACDQHpUil01uxv7-OMOwQ', 'Standards (أسئلة)', 'document'),
        'quality_ques_qa': ('BQACAgQAAxkBAAICWGndHYynVBF5_VGKAfnBa0p4iZWhAAJ8GgACDQHpUoq98uuyZXd-OwQ', 'Concept of Quality Assurance (أسئلة)', 'document'),
        'quality_ques_conc': ('BQACAgQAAxkBAAICY2ndHZROdcjTdE12isv4xysDQECbAAJ9GgACDQHpUn12xeC3DlXpOwQ', 'Concepts of Quality (أسئلة)', 'document'),
        'quality_ques_tqm': ('BQACAgQAAxkBAAICZGndHZS5U0vzueUE454kq9hg6DKJAAJ-GgACDQHpUuGu7uhKZosDOwQ', 'Total Quality Management (أسئلة)', 'document'),
        'health_edu_lect_eval': ('BQACAgQAAxkBAAICbWndHknRC_Yh0yGXozIe1YqpeQABEgACgxoAAg0B6VLooqSKEPPdkDsE', 'Evaluation in Health Education (شرح)', 'document'),
        'health_edu_lect_comm': ('BQACAgQAAxkBAAICbmndHkl1sJJ9N1SOg6wL74eXwoJRAAKEGgACDQHpUhcT6WL65GWFOwQ', 'Communication (شرح)', 'document'),
        'health_edu_lect_couns': ('BQACAgQAAxkBAAICb2ndHknvs_2zpzsYxcPoKGrxaU7SAAKFGgACDQHpUvOej30QAjTnOwQ', 'Counseling (شرح)', 'document'),
        'health_edu_lect_behav': ('BQACAgQAAxkBAAICcGndHkkSFPN2dQlYTdzA9cV0tLQsAAKGGgACDQHpUpE815zGgsegOwQ', 'Health and Human Behavior (شرح)', 'document'),
        'health_edu_lect_intro': ('BQACAgQAAxkBAAICcWndHknj4frekQc2lWKc7vfw0a-eAAKHGgACDQHpUitFy1dZkyiaOwQ', 'Introduction to Health Education (شرح)', 'document'),
        'health_edu_lect_plan': ('BQACAgQAAxkBAAICcmndHkkfAwu0Ijk2iWQb1awPFhAHAAKIGgACDQHpUm_ltXO2vxTzOwQ', 'Planning for health education (شرح)', 'document'),
        'health_edu_lect_mat': ('BQACAgQAAxkBAAICc2ndHkkxMy9Ib9uYlRT0Dwx-8Dc2AAKJGgACDQHpUun_GJHM37zgOwQ', 'Teaching Materials (شرح)', 'document'),
        'health_edu_lect_meth': ('BQACAgQAAxkBAAICdGndHkl1BzT-2hqk0ASG57RV_Sl1AAKKGgACDQHpUgE6LnatzfJfOwQ', 'Teaching Methods (شرح)', 'document'),
        'health_edu_ques_eval': ('BQACAgQAAxkBAAICfWndHrp34SN8-uVf6DdJjezfiwaTAAKLGgACDQHpUgfRkoecoy1yOwQ', 'Evaluation (أسئلة)', 'document'),
        'health_edu_ques_comm': ('BQACAgQAAxkBAAICfmndHrp7XBAbztyocRs-izwopKUpAAKMGgACDQHpUqVFGtY1iJlAOwQ', 'Communication (أسئلة)', 'document'),
        'health_edu_ques_couns': ('BQACAgQAAxkBAAICf2ndHrrhmgv5PuizdD0CB1KjiyyaAAKNGgACDQHpUlgRgMrMoRgXOwQ', 'Counseling (أسئلة)', 'document'),
        'health_edu_ques_behav': ('BQACAgQAAxkBAAICgGndHrq_gZ-GxW2F41FVHLnrf7lyAAKOGgACDQHpUq5OGSstUVy2OwQ', 'Behavior (أسئلة)', 'document'),
        'health_edu_ques_intro': ('BQACAgQAAxkBAAICgWndHrrMFkx0FrPdjTFMTcY_AAFX5wACjxoAAg0B6VJ2wQABHJ24I347BA', 'Introduction (أسئلة)', 'document'),
        'health_edu_ques_plan': ('BQACAgQAAxkBAAICgmndHrpr-nv-iMZtP8e5VT2XAcPGAAKQGgACDQHpUoOvMh0xnmjDOwQ', 'Planning (أسئلة)', 'document'),
        'health_edu_ques_mat': ('BQACAgQAAxkBAAICg2ndHrodBbb3nc_2df4XWROKbmCCAAKRGgACDQHpUvPEQxGaXP5aOwQ', 'Teaching Materials (أسئلة)', 'document'),
        'nurs_pr_lect_1': ('BQACAgQAAxkBAAICMGndHDclPWS1xlyun0mLWSWIFpzpAAJmGgACDQHpUgfd7-zn37tHOwQ', 'أساسيات تمريض عملي - ملف 1', 'document')
    },
    "settings": {
        "warning": "احنا مش مسامحين لاى شخص انوا ينشر او يعمل share لاى شخص) شايفك ياللى بتحاول😡",
        "dua": "اللهم اغفر لأموات المسلمين والمسلمات، واجعل قبورهم روضةً من رياض الجنة.",
        "vip_codes": [],
        "adhkar_morn": "☀️ **أذكار الصباح:**\n\n- آية الكرسي.\n- المعوذات (3 مرات).\n- أصبحنا وأصبح الملك لله، والحمد لله، لا إله إلا الله وحده لا شريك له...\n(يمكن للإدارة تعديل هذا النص من الإعدادات)",
        "adhkar_even": "🌙 **أذكار المساء:**\n\n- آية الكرسي.\n- المعوذات (3 مرات).\n- أمسينا وأمسى الملك لله، والحمد لله، لا إله إلا الله وحده لا شريك له...\n(يمكن للإدارة تعديل هذا النص من الإعدادات)"
    }
}

registered_users = load_data('users_db', {})
exams_db = load_data('exams_db', {})
content_db = load_data('content_db', default_content)

def is_allowed(uid):
    return int(uid) in BASE_ALLOWED_USERS or registered_users.get(str(uid), {}).get("is_vip", False)

def ensure_user(user):
    uid = str(user.id)
    if uid not in registered_users:
        registered_users[uid] = {"first_name": user.first_name, "is_vip": False, "is_banned": False, "total_score": 0}
        save_data('users_db', registered_users)
    return registered_users[uid]

def parse_mcq_text(text):
    questions = []
    q_blocks = re.split(r'\n\s*\d+[.)]\s*', text)
    for block in q_blocks:
        if not block.strip(): continue
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) < 3: continue
        q_text = lines[0]
        options, correct = [], " "
        for line in lines[1:]:
            if re.match(r'^[A-D][).]', line): options.append(line)
            elif "Correct Answer " in line or "الإجابة الصحيحة " in line:
                match = re.search(r'[A-D]', line)
                if match: correct = match.group(0)
        if q_text and len(options) >= 2 and correct:
            questions.append({"q": q_text, "options": options, "correct": correct})
    return questions

# --- الواجهة الرئيسية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)
    context.user_data.clear()
    if registered_users.get(str(user.id), {}).get("is_banned"): return

    if user.id == MY_ID:
        keyboard = [
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='menu_users'), InlineKeyboardButton("⚙️ الإعدادات", callback_data='menu_settings')],
            [InlineKeyboardButton("📁 إدارة المحتوى (إضافة/حذف)", callback_data='menu_content')],
            [InlineKeyboardButton("🎓 تصفح البوت كطالب", callback_data='year_1')]
        ]
        await update.message.reply_text("👑 **لوحة تحكم المدير العام**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        welcome_msg = f"مرحباً بك ({user.first_name}) اختر من الازرار ادناه ."
        reply_keyboard = [
            ["الفرقة الأولى 🎓", "الفرقة الثانية 🎓"],
            ["👤 البروفايل والأوائل", "🆔 معرفة الـ ID بتاعي"],
            ["📿 أذكار الصباح والمساء", "🍅 منظم الوقت"],
            ["📝 تسليم واجب", "💬 تواصل مع الإدارة"]
        ]
        await update.message.reply_text(welcome_msg, reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

async def show_subjects_keyboard(message, text):
    subjects = list(content_db['subjects'].values())
    keyboard = []
    for i in range(0, len(subjects), 2):
        keyboard.append(subjects[i:i+2])
    keyboard.append(["رجوع", "رجوع الى البداية"])
    await message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# --- معالجة الأزرار الشفافة ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer()
    
    if data == 'menu_users':
        keyboard = [
            [InlineKeyboardButton("📩 تصدير كملف", callback_data='admin_export'), InlineKeyboardButton("📊 الإحصائيات", callback_data='admin_stats')],
            [InlineKeyboardButton("🔍 معرفة الـ ID", callback_data='action_lookup_id'), InlineKeyboardButton("🎟️ كود VIP", callback_data='admin_gen_vip')],
            [InlineKeyboardButton("⭐ إضافة VIP", callback_data='action_add_vip'), InlineKeyboardButton("➖ إزالة VIP", callback_data='action_remove_vip')],
            [InlineKeyboardButton("🚫 حظر مستخدم", callback_data='action_ban'), InlineKeyboardButton("✅ فك حظر", callback_data='action_unban')],
            [InlineKeyboardButton("⬅️ القائمة الرئيسية", callback_data='back_main')]
        ]
        await query.edit_message_text("👥 **إدارة المستخدمين:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    elif data == 'action_lookup_id':
        context.user_data['admin_task'] = 'lookup_id'
        await query.message.reply_text("🔎 أرسل الـ ID الذي تريد البحث عنه لمراسلته:")
        return

    elif data == 'admin_gen_vip':
        new_code = f"VIP-{random.randint(10000, 99999)}"
        content_db['settings']['vip_codes'].append(new_code)
        save_data('content_db', content_db)
        await query.message.reply_text(f"🎟️ **كود VIP جديد:**\n`{new_code}`", parse_mode='Markdown')
        return
    elif data == 'admin_export':
        try: 
            with open('users_backup.json', 'w', encoding='utf-8') as f:
                json.dump(registered_users, f, ensure_ascii=False, indent=4)
            await context.bot.send_document(chat_id=uid, document=open('users_backup.json', 'rb'), filename="users_db.json", protect_content=True)
            os.remove('users_backup.json')
        except Exception as e: logging.error(f"Export Error: {e}")
        return 
    elif data == 'admin_stats':
        msg = f"📊 المستخدمين: {len(registered_users)}\n\n"
        for user_id, info in registered_users.items():
            status = "🔴 محظور" if info.get('is_banned') else ("🟢 VIP" if info.get('is_vip') else "⚪️ طالب")
            line = f"👤 {info.get('first_name', '')} | `{user_id}` | {status}\n"
            if len(msg) + len(line) > 3900:
                await context.bot.send_message(chat_id=uid, text=msg, parse_mode='Markdown')
                msg = ""
            msg += line
        if msg: await context.bot.send_message(chat_id=uid, text=msg, parse_mode='Markdown')
        return
    elif data.startswith('action_'):
        context.user_data['admin_task'] = data.replace('action_', '')
        await query.message.reply_text("أرسل ID المستخدم: ")
        return

    if data == 'menu_settings':
        keyboard = [
            [InlineKeyboardButton("📢 إرسال إشعار للكل", callback_data='sys_broadcast')],
            [InlineKeyboardButton("📝 إرسال كويز للكل", callback_data='sys_poll')],
            [InlineKeyboardButton("💾 نسخة احتياطية", callback_data='sys_backup')],
            [InlineKeyboardButton("💬 تعديل الرسائل الآلية", callback_data='sys_edit_msgs')],
            [InlineKeyboardButton("⬅️ رجوع", callback_data='back_main')]
        ]
        await query.edit_message_text("⚙️ **الإعدادات:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    elif data == 'sys_broadcast':
        context.user_data['admin_task'] = 'broadcast'
        await query.message.reply_text("📢 أرسل الرسالة للإذاعة: ")
        return
    elif data == 'sys_poll':
        context.user_data['admin_task'] = 'broadcast_poll'
        await query.message.reply_text("📝 أرسل: السؤال | إجابة1 | إجابة2 | رقم الصح")
        return
    elif data == 'sys_backup':
        try:
            for fname, d in [('users_db.json', registered_users), ('content_db.json', content_db), ('exams_db.json', exams_db)]:
                with open(fname, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=4)
                await context.bot.send_document(chat_id=uid, document=open(fname, 'rb'), protect_content=True)
                os.remove(fname)
        except Exception as e: logging.error(f"Backup Error: {e}")
        return
    elif data == 'sys_edit_msgs':
        keyboard = [
            [InlineKeyboardButton("📝 رسالة التحذير", callback_data='edit_msg_warning')],
            [InlineKeyboardButton("📝 رسالة الدعاء", callback_data='edit_msg_dua')],
            [InlineKeyboardButton("📝 أذكار الصباح", callback_data='edit_msg_adhkar_morn')],
            [InlineKeyboardButton("📝 أذكار المساء", callback_data='edit_msg_adhkar_even')],
            [InlineKeyboardButton("⬅️ رجوع", callback_data='menu_settings')]
        ]
        await query.edit_message_text("اختر للتعديل: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('edit_msg_'):
        context.user_data['admin_task'] = f"set_{data.replace('edit_msg_', '')}"
        await query.message.reply_text("أرسل النص الجديد الآن: ")
        return

    if data == 'menu_content':
        keyboard = [
            [InlineKeyboardButton("➕ إضافة مادة", callback_data='add_s'), InlineKeyboardButton("➕ إضافة قسم بسهولة", callback_data='add_c')],
            [InlineKeyboardButton("📁 رفع ملف/فيديو/صورة", callback_data='add_f')],
            [InlineKeyboardButton("🗑️ قائمة الحذف (ملف/قسم/مادة)", callback_data='del_menu')],
            [InlineKeyboardButton("📝 إضافة اختبار إلكتروني", callback_data='admin_add_exam')],
            [InlineKeyboardButton("⬅️ رجوع", callback_data='back_main')]
        ]
        await query.edit_message_text("📁 **إدارة المحتوى:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    elif data == 'add_s':
        context.user_data['admin_task'] = 'add_s'
        await query.message.reply_text("أرسل (اسم المادة - الرمز بالانجليزي)")
        return
    elif data == 'add_c':
        keyboard = [[InlineKeyboardButton(n, callback_data=f'set_s_c:{c}')] for c, n in content_db['subjects'].items()]
        await query.edit_message_text("اختر المادة لتضيف قسم جديد بداخلها: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('set_s_c:'):
        context.user_data['target_s'] = data.split(':')[1]
        context.user_data['admin_task'] = 'add_c'
        await query.message.reply_text("✨ أرسل اسم القسم مباشرة (مثلاً: Midterm، عملي، إلخ):")
        return
    elif data == 'add_f':
        keyboard = [[InlineKeyboardButton(n, callback_data=f'set_s_f:{c}')] for c, n in content_db['subjects'].items()]
        await query.edit_message_text("اختر المادة لرفع الملف أو الفيديو: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('set_s_f:'):
        s_code = data.split(':')[1]
        keyboard = [[InlineKeyboardButton(n, callback_data=f'up:{s_code}:{c}')] for c, n in content_db['categories'].get(s_code, {}).items()]
        await query.edit_message_text("اختر القسم لرفع الملف بداخله: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('up:'):
        _, s_code, c_code = data.split(':')
        context.user_data['upload_path'] = f"{s_code}_{c_code}"
        context.user_data['admin_task'] = 'upload'
        await query.message.reply_text("📤 **أرسل الآن (الملف، الفيديو، الصورة، أو الريكورد)**\n\n📌 *ملاحظة:* لا تنسَ كتابة اسم الملف في (الوصف/Caption) قبل الإرسال.", parse_mode='Markdown')
        return

    # قوائم الحذف (مادة، قسم، ملف)
    elif data == 'del_menu':
        keyboard = [[InlineKeyboardButton("🗑️ حذف ملف/فيديو", callback_data='del_f')], [InlineKeyboardButton("🗑️ حذف قسم بالكامل", callback_data='del_c')], [InlineKeyboardButton("🗑️ حذف مادة", callback_data='del_s')], [InlineKeyboardButton("⬅️ رجوع", callback_data='menu_content')]]
        await query.edit_message_text("ماذا تريد أن تحذف؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data == 'del_s':
        keyboard = [[InlineKeyboardButton(n, callback_data=f'dels:{c}')] for c, n in content_db['subjects'].items()]
        await query.edit_message_text("اختر المادة لحذفها: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('dels:'):
        sc = data.split(':')[1]
        content_db['subjects'].pop(sc, None)
        save_data('content_db', content_db)
        await query.edit_message_text("✅ تم حذف المادة بنجاح.")
        return
    elif data == 'del_c':
        keyboard = [[InlineKeyboardButton(n, callback_data=f'delc_s:{c}')] for c, n in content_db['subjects'].items()]
        await query.edit_message_text("اختر المادة التي بداخلها القسم المراد حذفه:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('delc_s:'):
        sc = data.split(':')[1]
        keyboard = [[InlineKeyboardButton(n, callback_data=f'delc_c:{sc}:{cc}')] for cc, n in content_db['categories'].get(sc, {}).items()]
        await query.edit_message_text("اختر القسم لحذفه نهائياً (سيتم مسح كل ملفاته):", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('delc_c:'):
        _, sc, cc = data.split(':')
        content_db['categories'].get(sc, {}).pop(cc, None)
        prefix = f"{sc}_{cc}"
        keys_to_del = [k for k in content_db['files'].keys() if k.startswith(prefix)]
        for k in keys_to_del: content_db['files'].pop(k, None)
        save_data('content_db', content_db)
        await query.edit_message_text("✅ تم حذف القسم وجميع ملفاته بنجاح.")
        return
    elif data == 'del_f':
        keyboard = [[InlineKeyboardButton(n, callback_data=f'delf_s:{c}')] for c, n in content_db['subjects'].items()]
        await query.edit_message_text("اختر المادة: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('delf_s:'):
        sc = data.split(':')[1]
        keyboard = [[InlineKeyboardButton(n, callback_data=f'delf_c:{sc}:{cc}')] for cc, n in content_db['categories'].get(sc, {}).items()]
        await query.edit_message_text("اختر القسم: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('delf_c:'):
        _, sc, cc = data.split(':')
        prefix = f"{sc}_{cc}"
        files = {k: v for k, v in content_db['files'].items() if k.startswith(prefix)}
        keyboard = [[InlineKeyboardButton(f"🗑️ {v[1]}", callback_data=f'delfile:{k}')] for k, v in files.items()]
        await query.edit_message_text("اختر الملف لحذفه: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('delfile:'):
        content_db['files'].pop(data.split(':')[1], None)
        save_data('content_db', content_db)
        await query.edit_message_text("✅ تم الحذف.")
        return

    # إضافة امتحان
    elif data == 'admin_add_exam':
        keyboard = [[InlineKeyboardButton(n, callback_data=f'ex_s:{c}')] for c, n in content_db['subjects'].items()]
        await query.edit_message_text("اختر المادة للاختبار: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('ex_s:'):
        context.user_data['exam_subj'] = data.split(':')[1]
        keyboard = [[InlineKeyboardButton("⚡ تفاعلي فوري", callback_data='ex_type_interactive')], [InlineKeyboardButton("📖 نظام بوكليت", callback_data='ex_type_booklet')]]
        await query.edit_message_text("اختر النظام: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data.startswith('ex_type_'):
        context.user_data['exam_type'] = data.replace('ex_type_', '')
        context.user_data['admin_task'] = 'upload_exam'
        await query.message.reply_text("✅ أرسل نص الأسئلة الآن.")
        return

    # تصفح الملفات
    elif data == 'year_1' and uid == MY_ID:
        keyboard = [[InlineKeyboardButton("📖 الترم الثاني", callback_data='year_1_term_2')], [InlineKeyboardButton("⬅️ الرئيسية", callback_data='back_main')]]
        await query.edit_message_text("اختر الفصل الدراسي:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif data == 'year_1_term_2':
        keyboard = [[InlineKeyboardButton(n, callback_data=f'subj:{c}')] for c, n in content_db['subjects'].items()]
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data='year_1')])
        await query.edit_message_text("اختر المادة:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
        
    elif data.startswith('subj:'):
        s_code = data.split(':')[1]
        subj_name = content_db['subjects'].get(s_code, "المادة")
        keyboard = [
            [InlineKeyboardButton("📁 تصفح المحتوى", callback_data=f'cats:{s_code}')], 
            [InlineKeyboardButton("📝 الاختبارات الإلكترونية", callback_data=f'view_ex:{s_code}')],
            [InlineKeyboardButton("⬅️ رجوع", callback_data='year_1_term_2')]
        ]
        await query.edit_message_text(f"مادة {subj_name}:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data.startswith('cats:'):
        s_code = data.split(':')[1]
        keyboard = [[InlineKeyboardButton(n, callback_data=f'list:{s_code}:{c}')] for c, n in content_db['categories'].get(s_code, {}).items()]
        await query.edit_message_text("اختر القسم: ", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data.startswith('list:'):
        _, s_code, c_code = data.split(':')
        prefix = f"{s_code}_{c_code}"
        files = {k: v for k, v in content_db['files'].items() if k.startswith(prefix)}
        if files:
            keyboard = [[InlineKeyboardButton(f"📄 {v[1]}", callback_data=f'send:{k}')] for k, v in files.items()]
            keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data=f'cats:{s_code}')])
            await query.edit_message_text("اختر الملف: ", reply_markup=InlineKeyboardMarkup(keyboard))
        else: await query.message.reply_text("لا يوجد ملفات هنا حالياً.")
        return

    elif data.startswith('send:'):
        file_key = data.split(':')[1]
        is_nurs2 = file_key.startswith('nurs2_')
        if not is_nurs2 and not is_allowed(uid): 
            return await query.message.reply_text("عفوا خاص بالvip يرجى الاشتراك اولا.")
        
        file_info = content_db['files'].get(file_key)
        if file_info: 
            f_id = file_info[0]
            f_type = file_info[2] if len(file_info) > 2 else 'document'
            cap = content_db['settings'].get('warning', '')
            
            is_protected = (uid != MY_ID)
            
            try:
                if f_type == 'video': await context.bot.send_video(chat_id=query.message.chat_id, video=f_id, caption=cap, protect_content=is_protected)
                elif f_type == 'audio': await context.bot.send_audio(chat_id=query.message.chat_id, audio=f_id, caption=cap, protect_content=is_protected)
                elif f_type == 'voice': await context.bot.send_voice(chat_id=query.message.chat_id, voice=f_id, caption=cap, protect_content=is_protected)
                elif f_type == 'photo': await context.bot.send_photo(chat_id=query.message.chat_id, photo=f_id, caption=cap, protect_content=is_protected)
                else: await context.bot.send_document(chat_id=query.message.chat_id, document=f_id, caption=cap, protect_content=is_protected)
            except:
                await context.bot.send_document(chat_id=query.message.chat_id, document=f_id, caption=cap, protect_content=is_protected)
            await context.bot.send_message(chat_id=query.message.chat_id, text=content_db['settings'].get('dua', ''))
        return

    # تشغيل الاختبارات 
    elif data.startswith('view_ex:'):
        s_code = data.split(':')[1]
        exams = {k: v for k, v in exams_db.items() if v['subj'] == s_code}
        if exams:
            keyboard = [[InlineKeyboardButton(f"✍️ {v['name']}", callback_data=f'startex_{k}')] for k, v in exams.items()]
            await query.edit_message_text("الاختبارات المتاحة: ", reply_markup=InlineKeyboardMarkup(keyboard))
        else: await query.message.reply_text("لا توجد اختبارات.")
        return
    elif data.startswith('startex_'):
        e_id = data.replace('startex_', '')
        exam = exams_db.get(e_id)
        if not exam: return
        is_nurs2 = exam.get('subj') == 'nurs2'
        if not is_nurs2 and not is_allowed(uid): 
            return await query.message.reply_text("عفوا خاص بالvip يرجى الاشتراك اولا.")
        
        context.user_data['exam_state'] = {'id': e_id, 'type': exam['type'], 'idx': 0, 'score': 0, 'answers': {}, 'start_time': time.time()}
        await render_exam_question(query, context)
        return
    elif data.startswith('ans_') or data.startswith('bkans_') or data.startswith('bknav_') or data == 'bk_submit':
        e_state = context.user_data.get('exam_state')
        if not e_state: return
        if time.time() - e_state['start_time'] > 1800:
            await query.edit_message_text("⏳ **انتهى الوقت المخصص للاختبار!** تم سحب الورقة.", parse_mode='Markdown')
            context.user_data.clear()
            return
        if data.startswith('ans_'):
            choice = data.split('_')[1]
            exam = exams_db[e_state['id']]
            q_data = exam['questions'][e_state['idx']]
            if choice == q_data['correct']:
                e_state['score'] += 1
                await query.answer("✅ إجابة صحيحة!", show_alert=True)
            else: await query.answer(f"❌ إجابة خاطئة!\nالصح هو ({q_data['correct']})", show_alert=True)
            e_state['idx'] += 1
            await render_exam_question(query, context)
        elif data.startswith('bkans_'):
            e_state['answers'][str(e_state['idx'])] = data.split('_')[1]
            await render_exam_question(query, context)
        elif data.startswith('bknav_'):
            nav_dir = data.split('_')[1]
            if nav_dir == 'next': e_state['idx'] += 1
            elif nav_dir == 'prev': e_state['idx'] -= 1
            await render_exam_question(query, context)
        elif data == 'bk_submit':
            exam = exams_db[e_state['id']]
            score = sum(1 for i, q in enumerate(exam['questions']) if e_state['answers'].get(str(i)) == q['correct'])
            total = len(exam['questions'])
            await finish_exam(query, context, score, total, exam['name'], exam['subj'])
        return

    # الأذكار (يتم جلبها من قاعدة البيانات)
    elif data == 'adhkar_morn':
        text = content_db['settings'].get('adhkar_morn', "☀️ أذكار الصباح غير متوفرة حالياً.")
        await query.message.reply_text(text, parse_mode='Markdown')
        return
    elif data == 'adhkar_even':
        text = content_db['settings'].get('adhkar_even', "🌙 أذكار المساء غير متوفرة حالياً.")
        await query.message.reply_text(text, parse_mode='Markdown')
        return

    elif data == 'back_main':
        await query.message.delete()
        await start(update, context)
        return

async def finish_exam(query, context, score, total, exam_name, subj_code):
    uid = str(query.from_user.id)
    if uid in registered_users:
        registered_users[uid]['total_score'] = registered_users[uid].get('total_score', 0) + score
        save_data('users_db', registered_users)
    await query.edit_message_text(f"🏁 **تم تسليم الاختبار!**\nالنتيجة النهائية: {score} من {total}", parse_mode='Markdown')
    await context.bot.send_message(chat_id=MY_ID, text=f"📊 **نتيجة اختبار**\nالطالب: {query.from_user.first_name}\nالنتيجة: {score}/{total}")
    context.user_data.clear()

async def render_exam_question(query, context):
    e_state = context.user_data['exam_state']
    exam = exams_db[e_state['id']]
    idx = e_state['idx']
    total = len(exam['questions'])
    if e_state['type'] == 'interactive' and idx >= total:
        return await finish_exam(query, context, e_state['score'], total, exam['name'], exam['subj'])
    q_data = exam['questions'][idx]
    time_left = max(0, 1800 - int(time.time() - e_state['start_time']))
    mins, secs = divmod(time_left, 60)
    text = f"⏳ الوقت المتبقي: {mins}:{secs:02d}\nالسؤال ({idx+1}/{total}):\n\n{q_data['q']}\n\n"
    for opt in q_data['options']: text += f"{opt}\n"
    keyboard = []
    if e_state['type'] == 'interactive':
        keyboard.append([InlineKeyboardButton(char, callback_data=f"ans_{char}") for char in ['A', 'B', 'C', 'D']])
    elif e_state['type'] == 'booklet':
        chosen = e_state['answers'].get(str(idx))
        keyboard.append([InlineKeyboardButton(f"✅ {char}" if chosen == char else char, callback_data=f"bkans_{char}") for char in ['A', 'B', 'C', 'D']])
        nav_row = []
        if idx > 0: nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data="bknav_prev"))
        nav_row.append(InlineKeyboardButton("🏁 تسليم", callback_data="bk_submit"))
        if idx < total - 1: nav_row.append(InlineKeyboardButton("التالي ➡️", callback_data="bknav_next"))
        keyboard.append(nav_row)
    try: await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except: pass 

# --- معالجة الرسائل النصية ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    task = context.user_data.get('admin_task')
    state = context.user_data.get('state')
    text = update.message.text if update.message.text else ""

    if text == "🆔 معرفة الـ ID بتاعي":
        await update.message.reply_text(f"الـ ID الخاص بحسابك هو:\n`{uid}`\n\n(اضغط على الرقم لنسخه وإرساله للإدارة)", parse_mode='Markdown')
        return
    
    elif text == "📿 أذكار الصباح والمساء":
        keyboard = [[InlineKeyboardButton("☀️ أذكار الصباح", callback_data='adhkar_morn')], [InlineKeyboardButton("🌙 أذكار المساء", callback_data='adhkar_even')]]
        await update.message.reply_text("اختر الأذكار:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if uid == MY_ID and task == 'lookup_id':
        target_id = text.strip()
        if target_id.isdigit():
            keyboard = [[InlineKeyboardButton("💬 مراسلة هذا الشخص", url=f"tg://user?id={target_id}")]]
            await update.message.reply_text(f"✅ تم العثور على رابط المراسلة للـ ID: `{target_id}`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else: await update.message.reply_text("❌ ID غير صحيح.")
        context.user_data.clear(); return

    if text.startswith("VIP-"):
        if text in content_db['settings'].get('vip_codes', []):
            content_db['settings']['vip_codes'].remove(text)
            registered_users[str(uid)]['is_vip'] = True
            save_data('users_db', registered_users)
            save_data('content_db', content_db)
            return await update.message.reply_text("🎉 تم تفعيل الـ VIP بنجاح.")
        else: return await update.message.reply_text("❌ الكود غير صحيح.")

    if text == "الفرقة الأولى 🎓":
        reply_keyboard = [["الترم الأول", "الترم الثاني"], ["رجوع الى البداية"]]
        await update.message.reply_text("اختر الترم:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        return
    elif text == "الترم الثاني":
        await show_subjects_keyboard(update.message, "اختر من الازرار ادناه .")
        return
    elif text == "رجوع الى البداية":
        await start(update, context)
        return
    elif text in ["الفرقة الثانية 🎓", "الترم الأول", "رجوع"]:
        await update.message.reply_text("قريباً...")
        return
    
    elif text == "👤 البروفايل والأوائل":
        user_info = ensure_user(update.effective_user)
        score = user_info.get('total_score', 0)
        status = "🌟 عضو VIP" if user_info.get('is_vip') else "⚪️ طالب عادي"
        prof_text = f"👤 **الملف الشخصي:**\n\nالاسم: {update.effective_user.first_name}\nالـ ID: `{uid}`\nالحالة: {status}\nإجمالي نقاطك: 🏆 {score} نقطة"
        await update.message.reply_text(prof_text, parse_mode='Markdown')
        return
    elif text == "🍅 منظم الوقت":
        await update.message.reply_text("🍅 **بدأ وقت التركيز (25 دقيقة)!**\nاقفل السوشيال ميديا وابدأ مذاكرة. سأقوم بتنبيهك عند انتهاء الوقت.")
        async def timer_task(chat_id, bot):
            await asyncio.sleep(25 * 60)
            try: await bot.send_message(chat_id, "⏰ **عاش يا بطل!**\nانتهت الـ 25 دقيقة، خد بريك 5 دقايق ☕", parse_mode='Markdown')
            except: pass
        asyncio.create_task(timer_task(update.message.chat_id, context.bot))
        return
    elif text == "📝 تسليم واجب":
        context.user_data['state'] = 'assignment'
        await update.message.reply_text("📝 **تسليم الواجب:**\nأرسل حلك الآن (صورة، ملف، أو نص) وسيتم إرساله للمطور.")
        return
    elif text == "💬 تواصل مع الإدارة":
        context.user_data['state'] = 'contact'
        await update.message.reply_text("💬 اكتب رسالتك ليتم إرسالها للمطور.")
        return

    elif text in content_db['subjects'].values():
        s_code = [k for k, v in content_db['subjects'].items() if v == text][0]
        keyboard = [[InlineKeyboardButton("📁 تصفح المحتوى", callback_data=f'cats:{s_code}')], [InlineKeyboardButton("📝 الاختبارات الإلكترونية", callback_data=f'view_ex:{s_code}')]]
        await update.message.reply_text(f"مادة {text}:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # مهام المطور (Admin)
    if uid == MY_ID and update.message.reply_to_message:
        try:
            target_id = update.message.reply_to_message.text.split("ID: ")[1].split()[0]
            await context.bot.copy_message(chat_id=target_id, from_chat_id=MY_ID, message_id=update.message.message_id, protect_content=True)
            return await update.message.reply_text("✅ تم إرسال الرد.")
        except: pass

    if state == 'assignment':
        await context.bot.send_message(chat_id=MY_ID, text=f"📚 **تسليم واجب جديد**\nالطالب: {update.effective_user.first_name}\nID: {uid}")
        await context.bot.copy_message(chat_id=MY_ID, from_chat_id=uid, message_id=update.message.message_id)
        await update.message.reply_text("✅ تم إرسال واجبك للمطور للتقييم.")
        context.user_data.clear(); return

    if state == 'contact':
        await context.bot.send_message(chat_id=MY_ID, text=f"📩 رسالة من: {update.effective_user.first_name}\nID: {uid}\n\n{text}")
        await update.message.reply_text("✅ تم الإرسال.")
        context.user_data.clear(); return

    if uid == MY_ID:
        if task == 'broadcast':
            for user_id in registered_users.keys():
                try: await context.bot.copy_message(chat_id=user_id, from_chat_id=MY_ID, message_id=update.message.message_id, protect_content=True)
                except: pass 
            await update.message.reply_text("✅ تم الإرسال.")
        elif task == 'broadcast_poll':
            try:
                parts = [p.strip() for p in text.split('|')]
                await update.message.reply_text("⏳ جاري الإرسال...")
                for user_id in registered_users.keys():
                    try: await context.bot.send_poll(chat_id=user_id, question=parts[0], options=parts[1:-1], type=Poll.QUIZ, correct_option_id=int(parts[-1])-1, protect_content=True)
                    except: pass
                await update.message.reply_text("✅ تم الإرسال.")
            except: await update.message.reply_text("❌ خطأ في الصيغة.")
        elif task == 'set_warning':
            content_db['settings']['warning'] = text
            save_data('content_db', content_db)
            await update.message.reply_text("✅ تم تعديل رسالة التحذير.")
        elif task == 'set_dua':
            content_db['settings']['dua'] = text
            save_data('content_db', content_db)
            await update.message.reply_text("✅ تم التعديل.")
        elif task == 'set_adhkar_morn':
            content_db['settings']['adhkar_morn'] = text
            save_data('content_db', content_db)
            await update.message.reply_text("✅ تم تعديل أذكار الصباح بنجاح.")
        elif task == 'set_adhkar_even':
            content_db['settings']['adhkar_even'] = text
            save_data('content_db', content_db)
            await update.message.reply_text("✅ تم تعديل أذكار المساء بنجاح.")
        elif task == 'add_s':
            name, code = text.split('-')
            content_db['subjects'][code.strip()] = name.strip()
            content_db['categories'][code.strip()] = {}
            save_data('content_db', content_db)
            await update.message.reply_text("✅ تم إضافة المادة.")
        elif task == 'add_c':
            name = text.strip()
            random_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            target_subj = context.user_data['target_s']
            content_db['categories'][target_subj][random_code] = name
            save_data('content_db', content_db)
            await update.message.reply_text(f"✅ تم إضافة قسم '{name}' بنجاح.")
        elif task in ['add_vip', 'remove_vip', 'ban', 'unban']:
            tid = text.strip()
            if tid not in registered_users: registered_users[tid] = {"first_name": "مضاف", "is_vip": False, "is_banned": False, "total_score": 0}
            if task == 'add_vip': registered_users[tid]['is_vip'] = True
            elif task == 'remove_vip': registered_users[tid]['is_vip'] = False
            elif task == 'ban': registered_users[tid]['is_banned'] = True
            elif task == 'unban': registered_users[tid]['is_banned'] = False
            save_data('users_db', registered_users)
            await update.message.reply_text("✅ تم.")
        elif task == 'upload_exam':
            questions = parse_mcq_text(text)
            if questions:
                e_id = str(uuid.uuid4())[:8]
                exams_db[e_id] = {"name": f"اختبار ({'تفاعلي' if context.user_data['exam_type']=='interactive' else 'بوكليت'})", "subj": context.user_data['exam_subj'], "type": context.user_data['exam_type'], "questions": questions}
                save_data('exams_db', exams_db)
                await update.message.reply_text(f"✅ تم إنشاء الاختبار بـ {len(questions)} سؤال!")
            else: await update.message.reply_text("❌ لم أستطع التحليل.")
        if task: context.user_data.clear(); return

# --- معالجة رفع الملفات ---
async def handle_docs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if context.user_data.get('state') == 'assignment': return await handle_msg(update, context)
    if uid == MY_ID and context.user_data.get('admin_task') == 'broadcast': return await handle_msg(update, context)
    if uid != MY_ID or context.user_data.get('admin_task') != 'upload': return
    
    path = context.user_data['upload_path']
    file_id = None
    file_type = 'document'
    
    if update.message.document: file_id = update.message.document.file_id
    elif update.message.video: file_id = update.message.video.file_id; file_type = 'video'
    elif update.message.audio: file_id = update.message.audio.file_id; file_type = 'audio'
    elif update.message.voice: file_id = update.message.voice.file_id; file_type = 'voice'
    elif update.message.photo: file_id = update.message.photo[-1].file_id; file_type = 'photo'
        
    fname = update.message.caption or "محتوى بدون اسم"
    if not file_id: return await update.message.reply_text("❌ نوع الملف غير مدعوم أو حدث خطأ.")
    
    content_db['files'][f"{path}_{uuid.uuid4().hex[:4]}"] = [file_id, fname, file_type]
    save_data('content_db', content_db)
    await update.message.reply_text(f"✅ تم رفع ({fname}) بنجاح.")
    context.user_data.clear()

def main():
    app = Application.builder().token(TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.PHOTO, handle_docs))
    
    app.run_polling()

if __name__ == '__main__': main()