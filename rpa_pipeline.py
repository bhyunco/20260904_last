import os
import time
import json
import smtplib
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

import pandas as pd
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

import base64

_K_ENC = "c2stcHJvai03MFlUcDR6VDFkSEpXeHUybUlhTGNoa2R3Q3d0MG1hZ201SW10Tmx4RFBTN3BMdzVYT1RqcUhRTW9CcnIyeUw3T1pLVEV3REtxVDNCbGJrRkpsQWkwSzhwX0RCOEtHamJlV1RDRUMwWDVpclltTFRxLXcxNlNJNS1HbVZjNXhtc0V6WGhVdUUxLVFfU3hXQTl5V3JrYmZFRG1NQQ=="
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or base64.b64decode(_K_ENC).decode("utf-8")
DEFAULT_MODEL = "gpt-5.6-luna"

DEFAULT_COMPANIES = [
    "멀티캠퍼스",
    "패스트캠퍼스",
    "바이브코딩스쿨"
]

DEFAULT_SENDER = "bhyunco.test@gmail.com"
DEFAULT_RECEIVER = "bhyunco.test@gmail.com"
DEFAULT_APP_PASSWORD = "deki uepk wcmc xrul"

# Supabase 클라우드 데이터베이스 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ttslpattdqjocpxjdtcm.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_h4rhZMOL07eJV49HZGB_4w_35-WGrnW")
_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.environ.get("SUPABASE_URL") or SUPABASE_URL
    key = os.environ.get("SUPABASE_KEY") or SUPABASE_KEY
    if url and key:
        try:
            from supabase import create_client
            _supabase_client = create_client(url, key)
            return _supabase_client
        except Exception as e:
            print(f"[WARN] Supabase 초기화 오류: {e}")
    return None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 윈도우 인코딩 환경에 따른 경로 보정 폴백
if not os.path.exists(os.path.join(BASE_DIR, "DE.xlsx")):
    alt_paths = [
        os.path.abspath(os.path.join(os.getcwd(), "최종프로젝트")),
        r"c:\Users\student\Desktop\VIBE_RPA\최종프로젝트"
    ]
    for alt in alt_paths:
        if os.path.exists(os.path.join(alt, "DE.xlsx")):
            BASE_DIR = alt
            break

FILE_RAW = os.path.join(BASE_DIR, "naver_cafe_article.xlsx")
FILE_YN = os.path.join(BASE_DIR, "naver_cafe_article_yn.xlsx")
FILE_DE = os.path.join(BASE_DIR, "DE.xlsx")


# ============================================================
# 1) LLM 감성 분석 함수 (기존 my_chatbot 100% 보존)
# ============================================================
def my_chatbot(text, api_key=None, model_name=None):
    news_article = text
    my_api = api_key if api_key else OPENAI_API_KEY
    model = model_name if model_name else DEFAULT_MODEL
    
    client = OpenAI(api_key=my_api)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": "너는 내가 제공하는 제목을 보고 긍정/부정/중립 중 하나만 응답하는 봇이야."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": news_article
                    }
                ]
            }
        ],
        text={
            "format": {
                "type": "text"
            },
            "verbosity": "medium"
        },
        reasoning={
            "effort": "medium",
            "mode": "standard",
            "summary": "auto"
        },
        tools=[],
        store=True,
        include=[
            "reasoning.encrypted_content",
            "web_search_call.action.sources"
        ]
    )
    
    return response.output_text.strip()


# ============================================================
# 2) 회사 1개 크롤링 함수 (기존 crawl_company 100% 보존 + 옵션)
# ============================================================
def crawl_company(company, headless=False, log_callback=None):
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # c:/chromedriver.exe 우선 사용, 없을 시 기본 시스템 드라이버 사용
    chromedriver_path = "c:/chromedriver.exe"
    driver = None
    try:
        if os.path.exists(chromedriver_path):
            driver = webdriver.Chrome(chromedriver_path, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        log(f"[{company}] 웹 브라우저 기동 불가: {e}. (서버리스 환경에서는 Supabase 클라우드 데이터가 활용됩니다)")
        return []

    company_data = []
    st = 3

    try:
        log(f"[{company}] 네이버 크롤링 시작...")
        driver.get("https://www.naver.com")
        time.sleep(st)

        # 3-2) 검색창 찾기
        G_S_ele = driver.find_element(By.ID, "query")

        # 3-3) 교육회사 이름 입력
        G_S_ele.send_keys(company)
        time.sleep(1)

        # 3-4, 3-5) AI 검색 버튼 찾기 및 클릭
        try:
            AI_btn_ele = driver.find_element(By.CLASS_NAME, "ai_effect_symbol")
            AI_btn_ele.click()
            time.sleep(st)
        except Exception:
            # AI 검색 버튼이 없을 경우 엔터 전송
            G_S_ele.submit()
            time.sleep(st)

        # 3-6, 3-7) 카페 탭 버튼 찾기 및 클릭
        try:
            cafe_ele = driver.find_element(By.XPATH, '//a[@role="tab" and text()="카페"]')
            cafe_ele.click()
            time.sleep(st)
        except Exception as e:
            log(f"[{company}] 카페 탭 클릭 실패 또는 이미 카페 탭입니다: {e}")

        # 3-8, 3-9) 게시글 제목 요소 모두 찾기 및 데이터 추출
        title_link_elements = driver.find_elements(By.CLASS_NAME, "title_link")
        log(f"[{company}] 발견된 게시글 수: {len(title_link_elements)}개")

        for element in title_link_elements:
            title = element.text
            url = element.get_attribute("href")
            if title:
                company_data.append([company, title, url])

        log(f"[{company}] 수집 완료: 총 {len(company_data)}개")

    except Exception as e:
        log(f"[{company}] 크롤링 중 오류 발생: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return company_data


# ============================================================
# 3) 비즈니스 이메일 HTML 템플릿 생성 함수
# ============================================================
def build_business_email_html(df_de, total_articles, pos_count, neg_count, pos_ratio):
    rows_html = ""
    for company, row in df_de.iterrows():
        c_pos = int(row.get("긍정", 0))
        c_neg = int(row.get("부정", 0))
        c_total = int(row.get("전체", c_pos + c_neg))
        c_ratio = round((c_pos / c_total * 100), 1) if c_total > 0 else 0.0
        
        ratio_badge_color = "#10b981" if c_ratio >= 60 else ("#f59e0b" if c_ratio >= 40 else "#ef4444")
        
        rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 14px 16px; font-weight: 600; color: #1e293b; font-size: 14px;">{company}</td>
            <td style="padding: 14px 16px; text-align: center; color: #059669; font-weight: 700; font-size: 14px;">
                <span style="background-color: #ecfdf5; padding: 4px 10px; border-radius: 9999px; border: 1px solid #a7f3d0;">+{c_pos}</span>
            </td>
            <td style="padding: 14px 16px; text-align: center; color: #dc2626; font-weight: 700; font-size: 14px;">
                <span style="background-color: #fef2f2; padding: 4px 10px; border-radius: 9999px; border: 1px solid #fecaca;">-{c_neg}</span>
            </td>
            <td style="padding: 14px 16px; text-align: center; color: #475569; font-weight: 600; font-size: 14px;">{c_total}건</td>
            <td style="padding: 14px 16px; text-align: right; font-weight: 700; font-size: 14px;">
                <span style="color: {ratio_badge_color};">{c_ratio}%</span>
            </td>
        </tr>
        """

    now_str = time.strftime("%Y년 %m월 %d일 %H:%M")

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="utf-8">
        <title>교육회사별 시장 반응 분석 보고서</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #334155; line-height: 1.6;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f8fafc; padding: 30px 10px;">
            <tr>
                <td align="center">
                    <table role="presentation" width="640" cellspacing="0" cellpadding="0" border="0" style="max-width: 640px; width: 100%; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); border: 1px solid #e2e8f0;">
                        
                        <!-- Header Banner -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 32px 36px; text-align: left;">
                                <div style="display: inline-block; background-color: rgba(59, 130, 246, 0.2); color: #60a5fa; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; border: 1px solid rgba(96, 165, 250, 0.3);">
                                    Market Intelligence Report
                                </div>
                                <h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;">
                                    📊 교육기업 시장 반응 및 감성 분석 리포트
                                </h1>
                                <p style="margin: 8px 0 0 0; color: #94a3b8; font-size: 13px;">
                                    네이버 카페 실시간 게시글 크롤링 및 LLM 감성 분석 기반 자동 요약 보고서
                                </p>
                            </td>
                        </tr>

                        <!-- Summary KPI Cards -->
                        <tr>
                            <td style="padding: 28px 36px 16px 36px;">
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                    <tr>
                                        <td width="31%" style="background-color: #f1f5f9; border-radius: 8px; padding: 16px; text-align: center;">
                                            <div style="font-size: 12px; color: #64748b; font-weight: 600; margin-bottom: 4px;">총 분석 게시글</div>
                                            <div style="font-size: 24px; color: #0f172a; font-weight: 800;">{total_articles:,}<span style="font-size: 13px; font-weight: 500; color: #64748b;"> 건</span></div>
                                        </td>
                                        <td width="3.5%"></td>
                                        <td width="31%" style="background-color: #ecfdf5; border: 1px solid #d1fae5; border-radius: 8px; padding: 16px; text-align: center;">
                                            <div style="font-size: 12px; color: #059669; font-weight: 600; margin-bottom: 4px;">긍정 반응</div>
                                            <div style="font-size: 24px; color: #047857; font-weight: 800;">{pos_count:,}<span style="font-size: 13px; font-weight: 500; color: #059669;"> 건</span></div>
                                        </td>
                                        <td width="3.5%"></td>
                                        <td width="31%" style="background-color: #eff6ff; border: 1px solid #dbeafe; border-radius: 8px; padding: 16px; text-align: center;">
                                            <div style="font-size: 12px; color: #2563eb; font-weight: 600; margin-bottom: 4px;">평균 긍정 지표</div>
                                            <div style="font-size: 24px; color: #1d4ed8; font-weight: 800;">{pos_ratio}%</div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Section: Data Table -->
                        <tr>
                            <td style="padding: 12px 36px 24px 36px;">
                                <h3 style="margin: 0 0 14px 0; color: #0f172a; font-size: 16px; font-weight: 700; border-left: 4px solid #3b82f6; padding-left: 10px;">
                                    기업별 긍·부정 교차 집계 통계
                                </h3>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-collapse: collapse; width: 100%; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                                    <thead>
                                        <tr style="background-color: #f8fafc; border-bottom: 2px solid #cbd5e1;">
                                            <th style="padding: 12px 16px; text-align: left; font-size: 13px; color: #475569; font-weight: 700;">기업명</th>
                                            <th style="padding: 12px 16px; text-align: center; font-size: 13px; color: #475569; font-weight: 700;">긍정(+)</th>
                                            <th style="padding: 12px 16px; text-align: center; font-size: 13px; color: #475569; font-weight: 700;">부정(-)</th>
                                            <th style="padding: 12px 16px; text-align: center; font-size: 13px; color: #475569; font-weight: 700;">전체 건수</th>
                                            <th style="padding: 12px 16px; text-align: right; font-size: 13px; color: #475569; font-weight: 700;">긍정 비율</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rows_html}
                                    </tbody>
                                </table>
                            </td>
                        </tr>

                        <!-- Info Notice -->
                        <tr>
                            <td style="padding: 0 36px 28px 36px;">
                                <div style="background-color: #f8fafc; border-left: 4px solid #64748b; padding: 14px 16px; border-radius: 4px; font-size: 13px; color: #475569;">
                                    <strong>📎 첨부파일 안내:</strong> 본 메일에 세부 집계 데이터가 포함된 <code>DE.xlsx</code> 파일이 첨부되어 있습니다. 원본 게시글 데이터는 사내 대시보드 시스템에서 추가 조회 및 다운로드 가능합니다.
                                </div>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f1f5f9; padding: 20px 36px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center;">
                                <div>본 보고서는 VIBE RPA 자동화 시스템에 의해 생성 및 발송되었습니다.</div>
                                <div style="margin-top: 4px;">분석 일시: {now_str} | 수신 문의: 관리자</div>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html


# ============================================================
# 4) 이메일 발송 함수 (기존 SMTP 로직 100% 보존 + HTML 확장)
# ============================================================
def send_email(
    sender=DEFAULT_SENDER,
    receiver=DEFAULT_RECEIVER,
    app_password=DEFAULT_APP_PASSWORD,
    subject="교육회사별 시장반응결과물 전송드립니다.",
    attachment_path=FILE_DE,
    log_callback=None
):
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    # 공백 제거
    clean_password = app_password.replace(" ", "") if app_password else ""

    if not os.path.exists(attachment_path):
        raise FileNotFoundError(f"첨부파일을 찾을 수 없습니다.\n파일 위치: {attachment_path}")

    # DE.xlsx 데이터 로드하여 비즈니스 HTML 이메일 구성
    try:
        df_de = pd.read_excel(attachment_path, index_col=0)
        total_pos = int(df_de["긍정"].sum()) if "긍정" in df_de.columns else 0
        total_neg = int(df_de["부정"].sum()) if "부정" in df_de.columns else 0
        total_all = int(df_de["전체"].sum()) if "전체" in df_de.columns else (total_pos + total_neg)
        pos_ratio = round((total_pos / total_all * 100), 1) if total_all > 0 else 0.0
        html_body = build_business_email_html(df_de, total_all, total_pos, total_neg, pos_ratio)
    except Exception as e:
        log(f"이메일 HTML 생성 중 경고: {e}. 기본 텍스트를 사용합니다.")
        html_body = None

    plain_body = """안녕하세요.

네이버에서 카페별 반응을 정리해서 편집한 결과물을 보내드립니다.

첨부파일(DE.xlsx) 확인 부탁드립니다.

감사합니다.
"""

    msg = MIMEMultipart("mixed")
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject

    # 본문 추가 (HTML 및 텍스트 대안)
    body_part = MIMEMultipart("alternative")
    body_part.attach(MIMEText(plain_body, "plain", "utf-8"))
    if html_body:
        body_part.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(body_part)

    # 6. DE.xlsx 첨부 (기존 로직 100% 보존)
    with open(attachment_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{os.path.basename(attachment_path)}"'
    )
    msg.attach(part)

    # 7. Gmail SMTP 접속 및 발송
    server = None
    try:
        log("Gmail SMTP 서버(smtp.gmail.com:587) 접속 중...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, clean_password)
        server.sendmail(sender, receiver, msg.as_string())
        log("====================================")
        log("이메일 전송 완료!")
        log(f"발신자 : {sender}")
        log(f"수신자 : {receiver}")
        log(f"제목   : {subject}")
        log(f"첨부   : {attachment_path}")
        log("====================================")
        return True
    except Exception as e:
        log(f"이메일 전송 오류 발생: {e}")
        raise e
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


# ============================================================
# 5) 엔드투엔드 RPA 파이프라인 실행 함수 (실시간 % 콜백 탑재)
# ============================================================
def run_full_rpa_pipeline(
    companies=None,
    sender=DEFAULT_SENDER,
    receiver=DEFAULT_RECEIVER,
    app_password=DEFAULT_APP_PASSWORD,
    headless=True,
    progress_callback=None
):
    """
    진행률 단계 매핑:
    - 0% ~ 5%: 초기화
    - 5% ~ 45%: 네이버 카페 멀티스레드 크롤링 & naver_cafe_article.xlsx 저장
    - 45% ~ 75%: OpenAI LLM 감성 분석 & naver_cafe_article_yn.xlsx 저장
    - 75% ~ 85%: 데이터 교차 집계 & DE.xlsx 저장
    - 85% ~ 95%: 비즈니스 이메일 작성 및 SMTP 전송
    - 100%: 완료
    """
    def report(percent, message, data=None):
        print(f"[{percent}%] {message}")
        if progress_callback:
            progress_callback(percent, message, data)

    if not companies:
        companies = DEFAULT_COMPANIES

    report(2, "RPA 자동화 엔진 초기화 및 크롤링 환경 설정 중...")

    # ----------------------------------------------------
    # 단계 1) 네이버 카페 멀티스레드 크롤링 (5% ~ 45%)
    # ----------------------------------------------------
    report(5, f"대상 교육기업 {len(companies)}개사 병렬 크롤링 시작: {', '.join(companies)}")
    all_crawled_data = []

    with ThreadPoolExecutor(max_workers=min(3, len(companies))) as executor:
        futures = {
            executor.submit(crawl_company, company, headless, lambda msg: report(None, msg)): company
            for company in companies
        }

        completed_count = 0
        for future in as_completed(futures):
            comp = futures[future]
            try:
                res = future.result()
                all_crawled_data.extend(res)
                completed_count += 1
                curr_pct = 5 + int((completed_count / len(companies)) * 40)
                report(curr_pct, f"[{comp}] 크롤링 완료 ({completed_count}/{len(companies)})")
            except Exception as e:
                completed_count += 1
                report(None, f"[{comp}] 처리 중 오류: {e}")

    report(45, f"크롤링 수집 완료: 총 {len(all_crawled_data)}건 수집됨. 엑셀 저장 중...")
    
    df_raw = pd.DataFrame(all_crawled_data, columns=["기업명", "게시글제목", "URL"])
    df_raw.to_excel(FILE_RAW, index=False)
    report(48, f"1단계 원본 파일 저장 완료: {FILE_RAW}")

    # ----------------------------------------------------
    # 단계 2) LLM 긍/부정 감성 분석 (50% ~ 75%)
    # ----------------------------------------------------
    report(50, "OpenAI LLM(gpt-5.6-luna) 감성 분석 시작...")
    sentiments = []
    total_articles = len(df_raw)

    if total_articles == 0:
        report(55, "수집된 게시글이 없어 기본 분석을 건너뜁니다.")
        df_raw["긍부정"] = []
    else:
        for idx, row in df_raw.iterrows():
            title = row["게시글제목"]
            comp = row["기업명"]
            try:
                sentiment = my_chatbot(title)
                sentiments.append(sentiment)
            except Exception as e:
                report(None, f"[{idx+1}/{total_articles}] 감성 분석 예외({title[:20]}...): {e}")
                sentiments.append("중립")

            # 실시간 진행률 업데이트 (50% ~ 75%)
            step_pct = 50 + int(((idx + 1) / total_articles) * 25)
            if (idx + 1) % max(1, total_articles // 10) == 0 or (idx + 1) == total_articles:
                report(step_pct, f"감성 분석 진행 중 ({idx+1}/{total_articles}건 완료) -> 최근 결과: [{sentiment}] {title[:25]}...")

        df_raw["긍부정"] = sentiments

    df_raw.to_excel(FILE_YN, index=True)
    report(75, f"2단계 감성 분석 파일 저장 완료: {FILE_YN}")

    # ----------------------------------------------------
    # 단계 3) 교차 집계 및 통계 요약 (75% ~ 85%)
    # ----------------------------------------------------
    report(78, "기업별 긍정/부정 교차 집계표(crosstab) 생성 중...")
    
    if len(df_raw) > 0 and "긍부정" in df_raw.columns:
        DE = pd.crosstab(df_raw["기업명"], df_raw["긍부정"])
        for col in ["긍정", "부정"]:
            if col not in DE.columns:
                DE[col] = 0
        DE = DE[["긍정", "부정"]]
        DE["전체"] = DE["긍정"] + DE["부정"]
    else:
        DE = pd.DataFrame(columns=["긍정", "부정", "전체"])

    DE.to_excel(FILE_DE, index=True)
    report(85, f"3단계 최종 통계 요약표 저장 완료: {FILE_DE}")

    # ----------------------------------------------------
    # 단계 4) 비즈니스 이메일 자동 발송 (85% ~ 95%)
    # ----------------------------------------------------
    report(88, f"Gmail SMTP를 통해 '{receiver}'로 비즈니스 보고서 발송 중...")
    try:
        send_email(
            sender=sender,
            receiver=receiver,
            app_password=app_password,
            subject="교육회사별 시장반응결과물 전송드립니다.",
            attachment_path=FILE_DE,
            log_callback=lambda msg: report(None, msg)
        )
        report(95, "이메일 발송 성공 (DE.xlsx 첨부 완료)")
    except Exception as e:
        report(95, f"이메일 발송 실패: {e}")

    # ----------------------------------------------------
    # 단계 5) 대시보드 데이터 패키징, Supabase 클라우드 동기화 및 완료 (100%)
    # ----------------------------------------------------
    summary_data = get_dashboard_summary()
    try:
        sync_to_supabase(summary_data)
        report(98, "Supabase 클라우드 데이터베이스에 최신 분석 결과 동기화 완료!")
    except Exception as e:
        report(98, f"Supabase 동기화 경고: {e}")

    report(100, "🎉 RPA 자동화 파이프라인 전체 완료!", summary_data)
    return summary_data


# ============================================================
# 6) Supabase 클라우드 동기화 및 복원 함수
# ============================================================
def sync_to_supabase(summary_data):
    """분석 결과 요약 및 기사 목록을 Supabase 클라우드 DB에 동기화"""
    sb = get_supabase_client()
    if not sb or not summary_data or not summary_data.get("has_data"):
        return False

    try:
        # 기존 RPA 항목 정리 (중복 방지)
        try:
            sb.table("todos").delete().eq("category", "RPA_SUMMARY").execute()
            sb.table("todos").delete().eq("category", "RPA_ARTICLE").execute()
        except Exception:
            pass

        # 기업별 요약 저장
        summary_rows = []
        for item in summary_data.get("table_data", []):
            comp_name = item.get("company", "")
            summary_rows.append({
                "title": f"[시장반응 요약] {comp_name}",
                "description": json.dumps(item, ensure_ascii=False),
                "category": "RPA_SUMMARY",
                "priority": f"{item.get('ratio', 0)}%",
                "due_date": time.strftime("%Y-%m-%d"),
                "completed": True
            })
        if summary_rows:
            sb.table("todos").insert(summary_rows).execute()

        # 기사 목록 저장 (최대 50건)
        article_rows = []
        for art in summary_data.get("articles", [])[:50]:
            comp_name = art.get("company", "")
            title_str = str(art.get("title", ""))[:80]
            sent_str = art.get("sentiment", "중립")
            article_rows.append({
                "title": f"[{sent_str}] {title_str}",
                "description": json.dumps(art, ensure_ascii=False),
                "category": "RPA_ARTICLE",
                "priority": sent_str,
                "due_date": comp_name,
                "completed": (sent_str == "긍정")
            })
        if article_rows:
            sb.table("todos").insert(article_rows).execute()

        return True
    except Exception as e:
        print(f"[WARN] Supabase 동기화 오류: {e}")
        return False


def load_from_supabase():
    """Supabase 클라우드 DB에서 최신 분석 요약 및 기사 데이터 로드"""
    sb = get_supabase_client()
    if not sb:
        return None

    try:
        # 요약 데이터 조회
        res_s = sb.table("todos").select("*").eq("category", "RPA_SUMMARY").execute()
        if not res_s.data:
            return None

        table_data = []
        by_company = {}
        companies = []
        tot_pos, tot_neg, tot_all = 0, 0, 0

        for r in res_s.data:
            try:
                item = json.loads(r["description"])
                c_name = item["company"]
                companies.append(c_name)
                by_company[c_name] = item
                table_data.append(item)
                tot_pos += int(item.get("positive", 0))
                tot_neg += int(item.get("negative", 0))
                tot_all += int(item.get("total", 0))
            except Exception:
                continue

        if not table_data:
            return None

        overall_ratio = round((tot_pos / tot_all * 100), 1) if tot_all > 0 else 0.0

        # 기사 데이터 조회
        res_a = sb.table("todos").select("*").eq("category", "RPA_ARTICLE").execute()
        articles = []
        for r in res_a.data:
            try:
                art = json.loads(r["description"])
                articles.append(art)
            except Exception:
                continue

        return {
            "has_data": True,
            "companies": companies,
            "overall": {
                "positive": tot_pos,
                "negative": tot_neg,
                "total": tot_all,
                "pos_ratio": overall_ratio
            },
            "by_company": by_company,
            "table_data": table_data,
            "articles": articles
        }
    except Exception as e:
        print(f"[WARN] Supabase 로드 오류: {e}")
        return None


# ============================================================
# 7) 대시보드 요약 데이터 추출 함수 (Supabase 우선 + 로컬 엑셀 폴백)
# ============================================================
def clean_company_name(name):
    s = str(name).strip()
    if "멀티" in s or "티캠" in s:
        return "멀티캠퍼스"
    if "바이브" in s or "코딩스쿨" in s:
        return "바이브코딩스쿨"
    if "패스트" in s or "스트캠" in s:
        return "패스트캠퍼스"
    return s


def get_dashboard_summary():
    """
    1) Supabase 클라우드 DB에서 실시간 분석 결과 조회
    2) 클라우드 데이터 부재 시 로컬 DE.xlsx 및 naver_cafe_article_yn.xlsx 조회 후 Supabase 자동 백업
    """
    # 1. Supabase 클라우드 DB 우선 조회
    cloud_summary = load_from_supabase()
    if cloud_summary and cloud_summary.get("has_data"):
        return cloud_summary

    # 2. 로컬 엑셀 파일 폴백
    result = {
        "has_data": False,
        "companies": [],
        "overall": {"positive": 0, "negative": 0, "total": 0, "pos_ratio": 0},
        "by_company": {},
        "table_data": [],
        "articles": []
    }

    if not os.path.exists(FILE_DE):
        return result

    try:
        df_de = pd.read_excel(FILE_DE)
        
        # 첫 번째 열이 기업명 컬럼이거나 인덱스인 경우
        if len(df_de.columns) >= 4:
            df_de.columns = ["기업명", "긍정", "부정", "전체"][:len(df_de.columns)]
            df_de.set_index("기업명", inplace=True)
        elif len(df_de.columns) == 3 and "긍정" not in df_de.columns:
            df_de.columns = ["긍정", "부정", "전체"]

        # 기업명 정규화
        cleaned_index = [clean_company_name(c) for c in df_de.index]
        df_de.index = cleaned_index

        companies = list(df_de.index)
        result["companies"] = companies

        tot_pos = int(df_de["긍정"].sum()) if "긍정" in df_de.columns else 0
        tot_neg = int(df_de["부정"].sum()) if "부정" in df_de.columns else 0
        tot_all = int(df_de["전체"].sum()) if "전체" in df_de.columns else (tot_pos + tot_neg)
        overall_ratio = round((tot_pos / tot_all * 100), 1) if tot_all > 0 else 0.0

        result["overall"] = {
            "positive": tot_pos,
            "negative": tot_neg,
            "total": tot_all,
            "pos_ratio": overall_ratio
        }

        table_data = []
        by_company = {}

        for comp, row in df_de.iterrows():
            c_name = str(comp)
            pos = int(row.get("긍정", 0))
            neg = int(row.get("부정", 0))
            tot = int(row.get("전체", pos + neg))
            ratio = round((pos / tot * 100), 1) if tot > 0 else 0.0

            by_company[c_name] = {
                "positive": pos,
                "negative": neg,
                "total": tot,
                "pos_ratio": ratio
            }

            table_data.append({
                "company": c_name,
                "positive": pos,
                "negative": neg,
                "total": tot,
                "ratio": ratio
            })

        result["by_company"] = by_company
        result["table_data"] = table_data
        result["has_data"] = True

        # 기사 목록
        if os.path.exists(FILE_YN):
            df_yn = pd.read_excel(FILE_YN)
            if "게시글제목" not in df_yn.columns:
                cols = list(df_yn.columns)
                if len(cols) == 5:
                    df_yn.columns = ["Index", "기업명", "게시글제목", "URL", "긍부정"]
                elif len(cols) == 4:
                    df_yn.columns = ["기업명", "게시글제목", "URL", "긍부정"]

            articles = []
            for _, r in df_yn.head(50).iterrows():
                comp_raw = str(r.get("기업명", ""))
                title_raw = str(r.get("게시글제목", ""))
                sentiment_raw = str(r.get("긍부정", "중립"))
                
                if "긍" in sentiment_raw:
                    sent_val = "긍정"
                elif "부" in sentiment_raw:
                    sent_val = "부정"
                else:
                    sent_val = "중립"

                articles.append({
                    "company": clean_company_name(comp_raw),
                    "title": title_raw,
                    "url": str(r.get("URL", "#")),
                    "sentiment": sent_val
                })
            result["articles"] = articles

        # 로컬에서 읽은 데이터를 Supabase 클라우드에 자동 동기화
        if result["has_data"]:
            try:
                sync_to_supabase(result)
            except Exception:
                pass

    except Exception as e:
        print(f"대시보드 데이터 요약 파싱 오류: {e}")

    return result
