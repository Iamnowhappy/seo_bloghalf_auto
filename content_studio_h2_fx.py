import os
from pathlib import Path
import re
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import webbrowser
from openai import OpenAI
import webbrowser


latest_keyword_path = None

# ==============================
# 🔁 FX 중복 방지 회전 규칙 (전역 상수)
# ==============================
ROLES = ["Hero", "Context", "Detail", "Wide"]
PEOPLE_RULE = ["with people", "no people"]
TIME_RULE = ["morning", "daytime", "evening", "night"]


# ==============================
# 🔐 OpenAI API KEY
# ==============================
import os
from openai import OpenAI

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=API_KEY)


# ==============================
# 📂 출력 폴더
# ==============================
BASE_OUTPUT_DIR = "gpt_outputs_html"

# ==============================
# 🧠 핫 키워드·제목 전용 SYSTEM_PROMPT
# - 이 프롬프트는
# HTML 생성과 완전히 분리된 “앞단 엔진” 이다.
# → 절대 HTML, FX, 이미지, 본문 생성하지 않는다.   
# ==============================
SYSTEM_PROMPT_KEYWORD = """
너는 ‘오늘 바로 써먹는 블로그 주제 코치’다.

너의 역할은
오늘 기준으로 실제 블로그에서 반응이 나오는
‘핫한 주제 + 제목’을
현실적인 시각으로 제안하는 것이다.

너는 키워드 분석가가 아니라,
상위노출 경험이 많은 블로그 운영자처럼 말해야 한다.

────────────────
[기본 전제]
────────────────
- 대형 이슈, 연예, 정치, 정책 주제는 개인 블로그에 불리하다
- 지금 잘 되는 글은 ‘생활 밀착 + 시즌 + 체감 경험’이다
- 네이버 블로그 기준으로 판단한다
- 대한민국 사용자 검색 행동을 기준으로 한다

────────────────
[출력 방식 – 매우 중요]
────────────────
❌ 키워드 표, 분석 리포트처럼 쓰지 말 것  
❌ 딱딱한 목록 나열 금지  

✅ 아래 구조와 말투를 반드시 따른다

────────────────

오늘 기준 핫한 블로그 주제 제안해줘

좋아요.
오늘 기준으로 ‘지금 쓰면 반응 나올 가능성 높은 주제’를
실제 블로그 운영 기준으로 정리해줄게요.

※ 전제
대기업·언론이 이미 점령한 키워드는 개인 블로그에 불리합니다.
오늘 유리한 건 ‘사람들이 실제로 겪고 검색하는 주제’입니다.

1️⃣ 지금 당장 반응 나오는 시즌형 주제  
- 왜 요즘 검색이 늘었는지
- 어떤 사람에게 체감되는지
- 어떤 식으로 글을 풀면 좋은지

예시 제목 형태:
- …
- …
- …

👉 지역 / 상황 결합 팁 자연스럽게 포함

2️⃣ 체험·후기형으로 특히 강한 주제  
- 요즘 소비 행동 변화 설명
- “직접 해봤다” 구조가 왜 먹히는지

예시 제목:
- …
- …

3️⃣ 네이버가 좋아하는 경험 기반 정보 주제  
- AI 글이 많아진 지금 왜 이런 글이 유리한지
- 사진·과정 설명 언급

4️⃣ 불안·걱정 해소형 주제  
- 사람들이 왜 검색하는지
- 클릭률이 높은 이유

5️⃣ 오늘 바로 써먹기 좋은 제목 조합  
- 실제 발행용 제목 형태로 제시
- 과장 없이 현실적인 제목

────────────────
[블로그 정체성 반영]
────────────────
사용자가 블로그 정체성을 제시한 경우,
해당 정체성에 맞춰 주제를 집중 추천한다.

예:
- AI 직장인 보고서
- 자영업
- 지역 서비스
- 생활 정보

────────────────
[랜덤 입력 처리]
────────────────
사용자가 “랜덤” 또는 “random”을 입력하면
오늘 날짜 기준으로
지금 쓰기 좋은 주제를 제안한다.

────────────────
[금지 규칙]
────────────────
- HTML 생성 금지
- 글 본문 작성 금지
- 이미지/FX 언급 금지
- AI, GPT, 모델 언급 금지
"""


# ==============================
# 🧠 SGC HTML 시스템 프롬프트(테마1 고정 버전)
# - 본문에 <script>/<style> 금지
# - 인라인 스타일만
# - ① HTML 본문 + ② 부가정보
# ==============================
SYSTEM_PROMPT_HTML = """
너는 “SGC_시각형 SEO 블로그 HTML 자동 생성기(티스토리용)”이다.
사용자가 제시한 주제/키워드를 바탕으로, 티스토리에 바로 붙여넣을 수 있는 완성형 HTML 본문과 부가 정보를 생성한다.

[출력 형식 — 반드시 고정]
- 아래 4개 토큰으로만 구분해 출력한다. (오탈자/변형 금지)
===HTML_START===
(여기에 HTML 본문만 출력)
===HTML_END===

===META_START===
(여기에 부가 정보만 출력)
===META_END===

[절대 규칙: 글자 수]
- HTML 본문(===HTML_START===~===HTML_END=== 구간)만 한글 기준 공백 포함 최소 3000자 이상 작성한다.
- 요약/축약 금지. 내용이 부족하다고 판단되면 각 h2 섹션의 문단과 사례를 늘려 분량을 채운다.

[HTML 본문 규칙]
- HEAD/BODY 태그 금지
- <style>, <script>, JSON-LD, application/ld+json 전부 금지
- 모든 스타일은 인라인 스타일만 사용
- HTML 외 설명 문장 출력 금지 (토큰 구간 외 텍스트 출력 금지)
- “메타 설명/키워드/제목”이라는 단어를 본문에 직접 노출하지 않는다.
- 이미지, FX, 시각화 “문장 생성” 자체는 허용하되(카드 등 UI 요소), 이미지 생성 지시문/프롬프트 문장/FX 관련 문장(예: “이런 이미지로 생성하세요”)은 본문에 절대 쓰지 않는다.

[컬러 테마: 블루-그레이 고정]
- 텍스트: #333
- 제목/포인트: #1a73e8
- 메타카드 배경: #f5f5f5
- 팁박스 배경: #e8f4fd / 좌측 보더 #1a73e8
- 주의박스 배경: #ffebee / 좌측 보더 #f44336
- 강조 배경: #fffde7
- 라인/보더: #ddd / #e0e0e0

[HTML 래퍼 — 반드시 본문 최상단에 그대로 사용]
<div style="color:#333;line-height:1.6;max-width:800px;margin:0 auto;font-size:16px;font-family:'Noto Sans KR',sans-serif;box-sizing:border-box;">
<p data-ke-size="size8">&nbsp;</p>

[본문 최상단 필수]
1) h1 제목 1개를 반드시 포함한다.
- 예: <h1 style="margin:0 0 14px 0;color:#1a73e8;font-size:28px;line-height:1.25;">...</h1>

2) 제목 바로 아래에 “요약 문장 카드(메타카드)”를 반드시 1개 넣는다.
- 단, 카드 안/밖 어디에도 “메타 설명”이라는 단어를 쓰지 않는다.
- 카드 형식 예:
<div style="background:#f5f5f5;border:1px solid #e0e0e0;border-radius:12px;padding:14px 16px;margin:0 0 18px 0;">
  <p style="margin:0;">...</p>
</div>

[섹션(h2) 구성 절대 규칙]
- h2는 최소 6개, 최대 8개로 “고정”한다. (6~8 범위에서 선택)
- 각 h2 섹션 시작 직전에 아래 점선 구분선을 반드시 삽입한다:
<hr style="border:none;border-top:1px dashed #ddd;margin:32px 0;">
- h2 태그 인라인 스타일은 반드시 아래를 포함한다:
  - margin-top:32px; margin-bottom:16px; color:#1a73e8;
- 각 h2 섹션은 아래 3요소를 “반드시” 포함한다:
  1) 핵심 설명 문단 2개 이상 (각 문단 4~6문장)
  2) Why(왜 중요한지) 또는 How(어떻게 활용하는지) 설명
  3) 실제 예시 또는 비교 설명 1회 이상
- 각 h2 섹션은 최소 350자 이상 작성한다.

[섹션 연결 문장 규칙]
- 각 h2 제목 바로 아래에 ‘연결 문단’을 먼저 작성한다.
- 연결 문단은 2~3문장으로 구성한다.
- 이전 섹션의 핵심을 직접 요약하지 말고,
  “이제 무엇을 볼 것인지”를 자연스럽게 예고한다.
- ‘앞서’, ‘이제’, ‘다음으로’, ‘이 지점에서’ 중 최소 1개를 반드시 사용한다.
- 설명 톤은 직장인 실무 관점으로 작성한다.

[본문 필수 요소 — 본문 안에 반드시 포함]
아래 요소들은 “전체 글에 최소 1회 이상” 반드시 등장해야 한다(누락 금지).

A) 시각화 카드(정보 카드) 최소 2개
- 카드 예시 스타일(구조만 참고, 내용은 주제에 맞게 작성):
<div style="border:1px solid #e0e0e0;border-radius:14px;padding:14px 16px;margin:14px 0;background:#fff;">
  <p style="margin:0 0 8px 0;color:#1a73e8;font-weight:700;">포인트</p>
  <p style="margin:0;">...</p>
</div>

B) 표(table) 최소 1개
- border/패딩을 인라인으로 명확히 지정한다.

C) 팁박스 최소 1개
<div style="background:#e8f4fd;border-left:6px solid #1a73e8;padding:14px 16px;border-radius:10px;margin:16px 0;">
  <p style="margin:0;font-weight:700;color:#1a73e8;">TIP</p>
  <p style="margin:8px 0 0 0;">...</p>
</div>

D) 주의박스 최소 1개
<div style="background:#ffebee;border-left:6px solid #f44336;padding:14px 16px;border-radius:10px;margin:16px 0;">
  <p style="margin:0;font-weight:700;color:#f44336;">주의</p>
  <p style="margin:8px 0 0 0;">...</p>
</div>

E) 예시박스 최소 1개
<div style="background:#fffde7;border:1px solid #e0e0e0;padding:14px 16px;border-radius:10px;margin:16px 0;">
  <p style="margin:0;font-weight:700;">예시</p>
  <p style="margin:8px 0 0 0;">...</p>
</div>

F) 목록(ul 또는 ol) 최소 1개
- 단순 나열이 아니라 “실행 순서/체크리스트” 형태로 작성한다.

G) FAQ 섹션(일반 HTML) 반드시 포함
- 최소 Q/A 5개 이상
- FAQ 역시 주제 맥락 + 실무 상황형 질문으로 작성

H) 본문 하단에 “핵심 키워드 요약 박스”를 반드시 포함
- 본문 마지막 부분(마무리 문단 직전 또는 직후)에 넣는다.
- 단, “키워드”라는 단어는 박스 제목에 직접 쓰지 말고 자연스럽게 표현한다(예: “핵심 포인트 한눈에 보기”).
- 박스 안에는 8~12개 키워드를 bullet로 정리한다.

[문체]
- 사람처럼 자연스럽게, 1인칭 공감 도입 포함
- 광고/홍보 느낌 금지
- AI 메타 발언 금지(“AI로 작성”, “모델”, “프롬프트” 등 금지)
- 직장인이 실제로 겪는 상황 → 문제 → 해석 → 정리 순서로 서술한다.

[분량/마무리 규칙]
- 마무리(결론) 섹션은 “별도의 h2로 만들지 말고” 본문 마지막에 자연스러운 문단으로 구성한다.
- 마무리 문단은 400~600자 범위로 제한한다(과도하게 길어지지 않게).
- 대신 본문 분량이 부족하면 결론을 늘리지 말고, h2 섹션의 사례/비교/설명을 늘려 분량을 채운다.

[부가 정보(===META_START=== 구간) 규칙 — 일반 텍스트]
- 아래 항목만 출력하고, 다른 설명은 금지한다.
1) 핵심 키워드 10개 (쉼표로 구분)
2) 대표 이미지 생성 프롬프트 1개 (한 줄)
3) SEO 제목 5개 (한 줄에 하나)

이제 사용자의 주제가 주어지면,
===HTML_START=== 구간에 HTML 본문만 먼저 출력하고,
===META_START=== 구간에 부가 정보를 출력하라.
"""

# ==============================
# 🧠 FX 시스템 프롬프트(핵심: h2별 1개 + 역할 회전 + 다양성 강제)
# - 코드블럭 규칙을 “프로그램/파일 저장”에 맞게 단순화
# - 여기서는 Image FX 중심으로 생성
# ==============================
SYSTEM_PROMPT_FX_H2 = """
너는 “FX 이미지 프롬프트 생성기(Image FX 중심)”다.
입력으로 주제와 섹션(소제목/요약)이 주어지면,
그 섹션에 맞는 고품질 이미지 프롬프트를 1개만 생성한다.

[절대 규칙]
- 출력은 프롬프트 문장 1줄만 출력한다. 설명 금지.
- 실행 JS/스크립트 언급 금지.
- 인물 등장 시 반드시 Korean man / Korean woman / Korean people 중 1개 이상 포함.
- Image FX 기준: photorealistic, highly detailed, soft natural light, ultra clear focus 포함.
- 과장된 예술 표현 금지.

[이미지 다양성 강제 규칙]
- 각 섹션은 역할(Role)이 주어진다: Hero / Context / Detail / Wide
- 동일한 구도/시점 반복 금지.
- Role에 맞게 촬영 거리/구도를 반드시 달리한다.
  - Hero: 가장 직관적 대표 구도(중간 거리, 주제 상징 강함)
  - Context: 상황+배경 맥락(조금 넓게, 행동/환경)
  - Detail: 손/표정/소품/텍스처 클로즈업(근접)
  - Wide: 공간 전체, 분위기/시간대(와이드)

────────────────────────
[이미지 다양성 강제 규칙 — 매우 중요]
────────────────────────

FX 이미지 프롬프트를 4개 생성할 경우,
각 Prompt는 반드시 서로 다른 “역할(Role)”을 가져야 한다.

다음 역할을 고정 적용한다.

Prompt #1 — Hero Image
- 대표 이미지
- 가장 직관적인 구도
- 주제 상징성이 가장 강해야 함

Prompt #2 — Context Scene
- 상황 설명 중심
- 인물의 행동, 배경 맥락이 드러나야 함
- Hero Image와 동일한 구도·시점 금지

Prompt #3 — Detail Shot
- 손, 표정, 시선, 소품 등 디테일에 집중
- 클로즈업 구도
- 인물 전체가 보이는 구도 금지

Prompt #4 — Wide / Atmosphere
- 공간 전체가 보이는 와이드 샷
- 배경·분위기·시간대 강조
- 인물은 작게 나오거나 등장하지 않아도 됨

모든 Prompt는
구도, 시점, 촬영 거리, 이미지 목적이
서로 명확히 달라야 하며,
비슷한 장면의 변주로 보이면 규칙 위반이다.


[중복 최소화 강제 규칙 — 인물·시간대 회전]
────────────────────────

각 섹션의 FX 이미지 프롬프트는
아래에서 지정된 “인물 유무”와 “시간대”를 반드시 따른다.

- 인물 있음:
  Korean man / Korean woman / Korean people 중 1개 이상 반드시 포함
- 인물 없음:
  사람 언급 금지, 공간·사물·환경 중심 묘사

시간대는 섹션별로 지정된 값을 반드시 포함한다.
(예: morning light, daytime, evening light, night atmosphere 등)

지정된 인물 유무 또는 시간대를 무시하거나
이전 섹션과 동일한 조건을 반복하면 규칙 위반이다.

[출력 형식]
- 프롬프트 1줄만 출력.
"""
# ==============================
# GPT 프롬프트용 함수: 제목 + 태그 생성
# ==============================
def generate_title_and_tags(topic: str):
    prompt = f"""
주제: {topic}

1. 네이버 블로그에 적합한 제목 1개 생성
2. 검색 노출에 유리한 태그 8~12개 생성
3. 출력 형식은 아래를 정확히 지켜라

[제목]
제목 내용

[태그]
태그1
태그2
태그3
...
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "너는 네이버 SEO에 최적화된 블로그 메타데이터 생성기다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )

    return res.choices[0].message.content.strip()

def open_naver_blog():
    webbrowser.open("https://blog.naver.com/hssgchng")

# ==============================
# ⛔ 키워드 호출함수
# ==============================
def call_keyword_gpt(user_prompt: str) -> str:
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_KEYWORD},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )
    return res.choices[0].message.content.strip()

# ==============================
# ⛔ 버튼에서 직접 호출하는 실행 함수 (이게 핵심)
# ==============================
def run_hot_keyword_finder():
    hint = entry.get().strip()
    if not hint:
        messagebox.showwarning("경고", "주제 힌트 또는 '랜덤'을 입력하세요.")
        return

    try:
        result, path = generate_hot_keywords_file(hint)

        fx_text.delete("1.0", tk.END)
        fx_text.insert(
            tk.END,
            f"✅ 핫 키워드가 파일로 저장되었습니다.\n\n"
            f"📂 저장 위치:\n{path}\n\n"
            f"--- 미리보기 ---\n\n"
            f"{result[:1200]}{'...' if len(result) > 1200 else ''}"
        )

        # ✅ 완료 메시지
        messagebox.showinfo(
            "완료",
            "핫 키워드·제목이 텍스트 파일로 저장되었습니다.\n"
            "확인을 누르면 저장된 폴더가 열립니다."
        )

        # ✅ 확인 누른 뒤 → 탐색기 자동 열기
        folder_path = os.path.dirname(path)
        os.startfile(folder_path)

    except Exception as e:
        messagebox.showerror("에러", str(e))



# ==============================
# ⛔ 금지 요소 필터 (HTML용)
# ==============================
def hard_block_html(text: str):
    banned = ["<script", "<style", "json-ld", "application/ld+json", "onclick="]
    low = text.lower()
    for b in banned:
        if b in low:
            raise ValueError(f"금지 요소 감지됨: {b}")
    return text
# ==============================
# ✂️ HTML에서 h2 섹션 추출
# ==============================
def extract_h2_sections(html_text: str, max_sections: int = 10, snippet_chars: int = 350):
    """
    HTML 본문에서 <h2> 섹션을 추출하여
    (h2 제목, 해당 섹션 요약 텍스트) 리스트 반환
    """

    # h2 태그 찾기
    h2_iter = list(re.finditer(r"<h2[^>]*>(.*?)</h2>", html_text, flags=re.IGNORECASE | re.DOTALL))

    def strip_tags(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    sections = []

    for i, match in enumerate(h2_iter):
        title_raw = match.group(1)
        title = strip_tags(title_raw)

        start = match.end()
        end = h2_iter[i + 1].start() if i + 1 < len(h2_iter) else len(html_text)
        body_raw = html_text[start:end]
        snippet = strip_tags(body_raw)[:snippet_chars]

        if title:
            sections.append((title, snippet))

        if len(sections) >= max_sections:
            break

    return sections

# ==============================
# 🧠키워드 분석 함수
# ==============================
def generate_hot_keywords_file(hint: str):
    global latest_keyword_path

    today = datetime.now().strftime("%Y-%m-%d_%H-%M")
    save_dir = "gpt_outputs_keywords"
    os.makedirs(save_dir, exist_ok=True)

    filename = f"hot_keyword_{today}.txt"
    path = os.path.join(save_dir, filename)

    user_prompt = f"""
오늘 날짜: {datetime.now().strftime("%Y-%m-%d")}

요청:
{hint}
"""

    result = call_keyword_gpt(user_prompt)

    with open(path, "w", encoding="utf-8") as f:
        f.write(result)

    latest_keyword_path = path
    return result, path



# ============================== 
# 키워드 주제 불러오는 함수 
# ============================== 
def generate_hot_keywords(): 
    hint = entry.get().strip() 
    if not hint: 
        messagebox.showerror("에러", "주제 힌트를 입력하세요") 
        return 
        
        generate_hot_keywords_file(hint)


# ==============================
# 🧠키워드 주제 파일오픈함수
# ==============================
import subprocess
import os

def open_keyword_file():
    if latest_keyword_path and os.path.exists(latest_keyword_path):
        os.startfile(latest_keyword_path)
    else:
        messagebox.showinfo("안내", "아직 생성된 키워드 파일이 없습니다.")


# ==============================
# 🧠실행 함수 (버튼용)
# ==============================
def run_keyword_finder():
    hint = entry.get().strip()
    if not hint:
        messagebox.showwarning("경고", "주제 힌트 또는 '랜덤'을 입력하세요.")
        return

    try:
        result = generate_hot_keywords(hint)
        fx_text.delete("1.0", tk.END)
        fx_text.insert(tk.END, result)
        messagebox.showinfo("완료", "핫 키워드·제목 분석이 완료되었습니다.")
    except Exception as e:
        messagebox.showerror("에러", str(e))


# ==============================
# 🧠meta.txt 저장 함수
# ==============================
def save_meta_file(out_dir: str, topic: str, meta_text: str):
    safe_topic = topic.replace(" ", "_")
    meta_path = os.path.join(out_dir, f"{safe_topic}_meta.txt")

    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(meta_text)

    return meta_path

# ==============================
# 🧠 GPT 호출: HTML 생성
# ==============================
def generate_html(topic: str) -> str:
    user_prompt = f"주제: {topic}\n\n위 주제로 ① HTML 본문과 ② 부가 정보를 생성하라."
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_HTML},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
    )
    return res.choices[0].message.content

# ==============================
# 💾 저장: HTML/메타 분리(B 방식)
# ==============================

def save_html_only(topic: str, full_text: str):
    today = datetime.now().strftime("%Y-%m-%d")
    safe_topic = topic.replace(" ", "_")
    out_dir = os.path.join(BASE_OUTPUT_DIR, today)
    os.makedirs(out_dir, exist_ok=True)

    html_path = os.path.join(out_dir, f"{safe_topic}.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_text.strip())

    return out_dir, html_path

# ==============================
# ✂️ HTML에서 h2 섹션 추출
# - 각 h2 제목 + 해당 섹션 내용 일부(요약용) 뽑기
# ==============================
def save_html_only(topic: str, full_text: str):
    today = datetime.now().strftime("%Y-%m-%d")
    safe_topic = topic.replace(" ", "_")
    out_dir = os.path.join(BASE_OUTPUT_DIR, today)
    os.makedirs(out_dir, exist_ok=True)

    html_path = os.path.join(out_dir, f"{safe_topic}.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_text.strip())

    return out_dir, html_path

# ==============================
# 🧠 GPT 호출: 섹션별 FX 프롬프트 1개 생성
# ==============================
def generate_fx_for_section(topic, h2_title, snippet, role, people_rule, time_rule):
    user_prompt = f"""
전체 주제: {topic}
섹션 소제목(h2): {h2_title}
섹션 요약: {snippet}

Role: {role}
People rule: {people_rule}
Time of day: {time_rule}

위 조건을 반드시 지켜
Image FX용 프롬프트 1줄만 생성하라.
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_FX_H2},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.65,
    )
    return res.choices[0].message.content.strip()



# ==============================
# 📸 이미지 placeholder 후처리 전용
# ==============================
def inject_placeholders_after_html(html_text: str):
    h2_pattern = re.compile(r"(<h2[^>]*>.*?</h2>)", re.I | re.S)
    count = 0

    def repl(match):
        nonlocal count
        count += 1
        return match.group(1) + f"""
<div style="margin:20px 0;padding:12px;
background:#f5f5f5;border-left:4px solid #1a73e8;
font-size:14px;color:#555;">
📌 이미지 위치 (Section {count})
</div>
"""

    return h2_pattern.sub(repl, html_text)


# ==============================
# 💾 저장: 섹션별 FX 프롬프트 파일
# ==============================
def save_fx_sections(out_dir: str, topic: str, fx_lines: list[str]):
    safe_topic = topic.replace(" ", "_").replace("/", "_")
    fx_path = os.path.join(out_dir, f"{safe_topic}_fx_sections.txt")
    with open(fx_path, "w", encoding="utf-8") as f:
        f.write("\n".join(fx_lines).strip() + "\n")
    return fx_path


# ==============================
# 🌐 링크 열기
# ==============================
def open_image_fx():
    webbrowser.open("https://labs.google/fx/ko/tools/whisk/project")

def open_codepen():
    webbrowser.open("https://codepen.io/pen")

# ==============================
# 📋 복사
# ==============================
def copy_fx_to_clipboard():
    txt = fx_text.get("1.0", tk.END).strip()
    if not txt:
        messagebox.showwarning("경고", "복사할 FX 결과가 없습니다.")
        return
    root.clipboard_clear()
    root.clipboard_append(txt)
    messagebox.showinfo("완료", "FX 섹션 프롬프트를 클립보드에 복사했습니다.")

# ==============================
# 📂 파일 열기(탐색기)
# ==============================
def open_file(path: str):
    if not path or not os.path.exists(path):
        messagebox.showwarning("경고", "파일 경로가 유효하지 않습니다.")
        return
    os.startfile(path)
# ==============================
# 📂 본문 키워드 저장함수
# ==============================
def save_split_html(topic: str, full_text: str):
    import os
    from datetime import datetime

    base_dir = "gpt_outputs_html"
    os.makedirs(base_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")

    safe_topic = topic.replace(" ", "_")

    html_path = os.path.join(
        base_dir, f"{ts}_{safe_topic}_본문.html"
    )
    meta_path = os.path.join(
        base_dir, f"{ts}_{safe_topic}_제목_키워드.txt"
    )

    # ====== HTML / META 분리 ======
    if "===META_START===" in full_text:
        html_part, meta_part = full_text.split("===META_START===", 1)
    else:
        html_part = full_text
        meta_part = ""

    html_part = html_part.replace("===HTML_START===", "").replace("===HTML_END===", "").strip()
    meta_part = meta_part.replace("===META_END===", "").strip()

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_part)

    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(meta_part)

    return base_dir, html_path, meta_path

# ==============================
# 📂 마우스 우클릭시 간단메뉴
# ==============================
def add_context_menu(widget):
    menu = tk.Menu(widget, tearoff=0)

    menu.add_command(label="잘라내기", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="복사", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="붙여넣기", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="전체 선택", command=lambda: widget.select_range(0, tk.END))

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show_menu)
    
# ==============================
# ▶ 제목+태그 파일 열기 안전장치
# ==============================    
def open_meta_file():
    if latest_meta_path and os.path.exists(latest_meta_path):
        os.startfile(latest_meta_path)
    else:
        messagebox.showinfo("안내", "아직 생성된 제목+태그 파일이 없습니다.")

# ==============================
# ▶ 실행: HTML → 저장 → h2 추출 → 섹션별 FX 생성 → 저장
# ==============================
latest_html_path = ""
latest_fx_path = ""
latest_meta_path = "" 
def run_all():
    global latest_html_path, latest_fx_path, latest_meta_path

    topic = entry.get().strip()
    if not topic:
        messagebox.showwarning("경고", "주제를 입력하세요.")
        return

    try:
        # 1) HTML + META 생성 (1회만)
        full_text = generate_html(topic)

        # 2) HTML / META 분리 저장
        out_dir, html_path, meta_path = save_split_html(topic, full_text)
        latest_html_path = html_path
        latest_meta_path = meta_path

        # 3) 제목 + 태그 생성
        meta_text = generate_title_and_tags(topic)
        meta_path = save_meta_file(out_dir, topic, meta_text)
        latest_meta_path = meta_path

        # 4) h2 기반 FX 생성
        max_sections = int(max_sections_var.get())
        fx_lines = postprocess_fx(
            html_path=html_path,
            topic=topic,
            max_sections=max_sections
        )

        fx_path = save_fx_sections(out_dir, topic, fx_lines)
        latest_fx_path = fx_path

        # 5) UI 출력
        fx_text.delete("1.0", tk.END)
        fx_text.insert(tk.END, "\n".join(fx_lines).strip())

        # 6) 완료 안내
        messagebox.showinfo(
            "작업 완료",
            "HTML · FX · 제목/태그 생성이 완료되었습니다.\n\n"
            "확인을 누르면 결과 폴더가 열립니다."
        )

        # 7) 결과 폴더 자동 열기 (안전)
        try:
            if out_dir and os.path.exists(out_dir):
                os.startfile(out_dir)
        except Exception:
            pass

    except Exception as e:
        messagebox.showerror("에러", str(e))


# ==============================
# 🧠 FX 후처리 (HTML 생성 이후 전용)
# ==============================
def postprocess_fx(html_path: str, topic: str, max_sections: int):
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    sections = extract_h2_sections(html, max_sections=max_sections)

    if not sections:
        raise ValueError("HTML에서 h2 섹션을 찾지 못했습니다. (h2가 생성되었는지 확인)")

    fx_lines = []

    for i, (h2_title, snippet) in enumerate(sections, start=1):
        role = ROLES[(i - 1) % len(ROLES)]
        people = PEOPLE_RULE[(i - 1) % len(PEOPLE_RULE)]
        time_of_day = TIME_RULE[(i - 1) % len(TIME_RULE)]

        fx_prompt = generate_fx_for_section(
            topic, h2_title, snippet, role, people, time_of_day
        )

        fx_lines.append(f"[{i}] ({role} | {people} | {time_of_day}) {h2_title}")
        fx_lines.append(fx_prompt)
        fx_lines.append("")

    return fx_lines

def open_naver_blog():
    webbrowser.open("https://blog.naver.com/hssgchng")


# ==============================
# 🖥 GUI
# ==============================
root = tk.Tk()
root.title("SGC HTML + h2별 FX 프롬프트 자동 생성기")
root.geometry("980x720")

top_frame = tk.Frame(root)
top_frame.pack(pady=10)

tk.Label(top_frame, text="주제 입력").grid(row=0, column=0, padx=6, pady=6, sticky="e")
entry = tk.Entry(top_frame, width=70)
entry.grid(row=0, column=1, padx=6, pady=6, sticky="w")
add_context_menu(entry)

tk.Label(top_frame, text="h2 최대 개수").grid(row=0, column=2, padx=6, pady=6, sticky="e")
max_sections_var = tk.StringVar(value="8")  # 기본 8개
tk.Spinbox(top_frame, from_=3, to=20, width=5, textvariable=max_sections_var).grid(row=0, column=3, padx=6, pady=6)

tk.Button(top_frame, text="HTML 생성 → h2별 FX 자동", command=run_all, height=1, width=22).grid(row=0, column=4, padx=10, pady=6)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=6)

add_context_menu(entry)

tk.Button(
    btn_frame,
    text="핫 키워드·제목 열기",
    command=open_keyword_file,
    width=16
).grid(row=0, column=6, padx=6)

tk.Button(
    top_frame,
    text="🔥 핫 키워드·제목 찾기",
    command=run_hot_keyword_finder,   # ← 여기!
    height=1,
    width=20
).grid(row=1, column=1, padx=6, pady=6, sticky="w")


tk.Button(btn_frame, text="CodePen 열기", command=open_codepen, width=16).grid(row=0, column=1, padx=6)
tk.Button(btn_frame, text="내 네이버 블로그", command=open_naver_blog,  width=16).grid(row=0, column=5, padx=6)
tk.Button(btn_frame, text="Image FX 열기", command=open_image_fx, width=16).grid(row=0, column=0, padx=6)
tk.Button(btn_frame, text="HTML 열기", command=lambda: open_file(latest_html_path), width=16).grid(row=0, column=3, padx=6)
tk.Button(btn_frame, text="FX 파일 열기", command=lambda: open_file(latest_fx_path), width=16).grid(row=0, column=4, padx=6)
tk.Button(btn_frame, text="제목+태그 열기",command=open_meta_file, width=16).grid(row=0, column=6, padx=6)
tk.Button(btn_frame, text="FX 결과 복사", command=copy_fx_to_clipboard, width=16).grid(row=0, column=2, padx=6)

tk.Label(root, text="h2 섹션별 FX 프롬프트 결과").pack(pady=6)

fx_text = tk.Text(root, height=28, width=120)
fx_text.pack(padx=10, pady=6)
add_context_menu(fx_text)

root.mainloop()
# ==============================
# 🖱 Entry 우클릭 컨텍스트 메뉴
# ==============================

def create_entry_context_menu(widget):
    menu = tk.Menu(widget, tearoff=0)

    menu.add_command(label="잘라내기", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="복사", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="붙여넣기", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="전체 선택", command=lambda: widget.select_range(0, tk.END))

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show_menu)
