import streamlit as st
import re
from textwrap import dedent
from phi.agent import Agent
from phi.model.groq import Groq
from phi.tools.duckduckgo import DuckDuckGo
from icalendar import Calendar, Event
from datetime import datetime, timedelta

# دالة توليد ملف التقويم (ICS)
def generate_ics_content(plan_text: str, start_date: datetime = None) -> bytes:
    cal = Calendar()
    cal.add('prodid', '-//AI Travel Planner//github.com//')
    cal.add('version', '2.0')

    if start_date is None:
        start_date = datetime.today()

    day_pattern = re.compile(r'Day (\d+)[:\s]+(.*?)(?=Day \d+|$)', re.DOTALL)
    days = day_pattern.findall(plan_text)

    if not days:
        event = Event()
        event.add('summary', "Travel Itinerary")
        event.add('description', plan_text)
        event.add('dtstart', start_date.date())
        event.add('dtend', start_date.date())
        event.add("dtstamp", datetime.now())
        cal.add_component(event)  
    else:
        for day_num, day_content in days:
            day_num = int(day_num)
            current_date = start_date + timedelta(days=day_num - 1)
            
            event = Event()
            event.add('summary', f"Day {day_num} Itinerary")
            event.add('description', day_content.strip())
            event.add('dtstart', current_date.date())
            event.add('dtend', current_date.date())
            event.add("dtstamp", datetime.now())
            cal.add_component(event)

    return cal.to_ical()

# إعداد واجهة التطبيق
st.set_page_config(page_title="AI Travel Planner", page_icon="✈️", layout="wide")
st.title("✈️ AI Travel Planner (Powered by Groq)")
st.caption("خطط لرحلتك القادمة بذكاء وسرعة فائقة باستخدام أحدث نماذج Groq المتاحة")

if 'itinerary' not in st.session_state:
    st.session_state.itinerary = None

# إضافة قائمة منسدلة لاختيار النموذج النشط حالياً في Groq لتجنب مشاكل الإيقاف المستقبلي
available_models = [
    "llama-3.3-70b-versatile",
    "llama-3.3-70b-specdec",
    "llama-3.1-8b-instant"
]
selected_model = st.selectbox("اختر نموذج الذكاء الاصطناعي المستهدف:", available_models)

try:
    # إعداد العميل الذكي بالنموذج المختار من الواجهة
    researcher = Agent(
        name="Researcher",
        model=Groq(id=selected_model),
        tools=[DuckDuckGo()],
        description="You are a world-class travel researcher. Search the web for accommodations and activities.",
        instructions=["Find the best 3 search terms for the destination.", "Return the top results in a clean format."],
        markdown=True
    )

    planner = Agent(
        name="Planner",
        model=Groq(id=selected_model),
        description="You are a senior travel planner.",
        instructions=[
            "Create a detailed day-by-day itinerary based on the research results.",
            "Structure it cleanly using 'Day 1', 'Day 2', etc., so the calendar tool can read it.",
            "Please provide the final output in Arabic language beautifully."
        ],
        markdown=True
    )

    # خانات الإدخال للواجهة
    destination = st.text_input("إلى أين تريد السفر؟ (مثال: باريس، دبي، تايلند)")
    num_days = st.number_input("كم عدد أيام الرحلة؟", min_value=1, max_value=30, value=5)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("ابنِ لي الخطة الآن 🚀"):
            if destination:
                with st.spinner("جاري البحث وجمع المعلومات عن الوجهة..."):
                    research_results = researcher.run(f"Research {destination} for a {num_days} day trip")
                    
                with st.spinner("جاري صياغة الجدول السياحي باللغة العربية..."):
                    prompt = f"""
                    Destination: {destination}
                    Duration: {num_days} days
                    Research Results: {research_results.content}
                    """
                    response = planner.run(prompt)
                    st.session_state.itinerary = response.content
            else:
                st.warning("الرجاء كتابة الوجهة أولاً!")

    # عرض النتيجة وزر التحميل
    if st.session_state.itinerary:
        st.markdown(st.session_state.itinerary)
        
        with col2:
            ics_content = generate_ics_content(st.session_state.itinerary)
            st.download_button(
                label="تحميل الجدول كملف تقويم (.ics) 📅",
                data=ics_content,
                file_name="travel_itinerary.ics",
                mime="text/calendar"
            )
            
except Exception as e:
    st.error(f"حدث خطأ أثناء الاتصال بالنموذج المختار. جرب تغيير النموذج من القائمة العلوية. نوع الخطأ: {e}")