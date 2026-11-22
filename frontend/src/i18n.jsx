import { createContext, useContext, useEffect, useState } from "react";

// English text is the key; Korean is looked up, and anything missing falls back to English.
const KO = {
  // navigation
  Resume: "이력서",
  Matches: "추천",
  "All jobs": "전체 공고",
  Saved: "저장됨",
  "Log in": "로그인",
  "Log out": "로그아웃",
  "Dark mode": "다크 모드",
  "Light mode": "라이트 모드",
  "Page not found.": "페이지를 찾을 수 없어요.",
  "Loading…": "불러오는 중…",

  // landing / auth
  "AI job search for Korea": "한국 취업을 위한 AI 잡 서치",
  "Your resume in.": "이력서를 올리면,",
  "Live matches out.": "맞춤 공고가 바로.",
  "Upload a PDF. We read your skills, search Wanted, Jumpit and JobKorea for fresh internships and entry-level roles, and rank them with a score you can understand.":
    "PDF 이력서를 올리세요. 보유 기술을 읽고 원티드·점핏·잡코리아에서 신입·인턴 공고를 실시간으로 찾아, 이해하기 쉬운 점수로 순위를 매깁니다.",
  "Read resume": "이력서 분석",
  "Search 3 job sites": "채용 사이트 3곳 검색",
  "Score & skill gap": "점수 · 부족한 기술",
  "Create your account": "계정 만들기",
  "Welcome back": "다시 오신 것을 환영해요",
  "Free. Your resume is visible only to you.": "무료입니다. 이력서는 본인만 볼 수 있어요.",
  "Log in to see your matches.": "로그인하고 추천 공고를 확인하세요.",
  Name: "이름",
  Email: "이메일",
  Password: "비밀번호",
  "Create account": "계정 만들기",
  "Already have an account?": "이미 계정이 있나요?",
  "New here?": "처음이신가요?",
  "Create an account": "계정 만들기",
  "Your account and all your data were deleted.": "계정과 모든 데이터가 삭제되었어요.",
  Wanted: "원티드",
  Jumpit: "점핏",
  JobKorea: "잡코리아",

  // resume
  "Sign up": "회원가입",
  "Upload resume": "이력서 업로드",
  "View matches": "추천 보기",
  "Replace your resume": "이력서 교체",
  "Upload your resume": "이력서 업로드",
  "PDF only, up to 5 MB. Use a PDF exported from Word / Google Docs — scanned images can't be read.":
    "PDF만 가능, 최대 5MB. Word·구글 문서에서 내보낸 PDF를 사용하세요. 스캔 이미지는 읽을 수 없어요.",
  "Drop your PDF here": "PDF를 여기에 끌어다 놓으세요",
  "or tap to choose a file": "또는 눌러서 파일 선택",
  "Ready to analyze": "분석 준비 완료",
  "Upload & find jobs": "업로드하고 공고 찾기",
  "Reading your PDF": "PDF 읽는 중",
  "Extracting skills": "기술 추출 중",
  "Searching Wanted, Jumpit, JobKorea": "원티드·점핏·잡코리아 검색 중",
  "Scoring matches": "매칭 점수 계산 중",
  "{n} postings found right now": "지금 공고 {n}개 발견",
  "on Wanted, Jumpit and JobKorea for your skills.": "원티드·점핏·잡코리아에서 내 기술 기준으로 찾았어요.",
  "Your matches are ready.": "추천이 준비됐어요.",
  "The live search had nothing new this time, so they come from the postings already collected.":
    "이번 실시간 검색에서는 새 공고가 없어 기존에 모은 공고로 추천했어요.",
  "See your matches": "추천 공고 보기",
  "Extracted from your resume": "이력서에서 추출한 정보",
  "method: AI (LLM)": "방식: AI (LLM)",
  "method: keyword matching": "방식: 키워드 매칭",
  Education: "학력",
  Experience: "경력",
  "not found": "찾지 못함",
  "{n} year(s)": "{n}년",
  "No professional experience found": "경력 정보 없음",
  "Skills ({n})": "기술 ({n})",
  "Check the list: remove anything wrong and add what was missed.": "목록을 확인하세요. 틀린 것은 지우고 빠진 것은 추가하세요.",
  "Add a skill, e.g. Docker": "기술 추가 (예: Docker)",
  Add: "추가",
  "Save skills": "기술 저장",
  "Saving…": "저장 중…",
  "Saved ✓": "저장됨 ✓",
  "See recommendations": "추천 보기",
  "Your data": "내 데이터",
  "Your resume is visible only to you. You can delete everything at any time.":
    "이력서는 본인만 볼 수 있어요. 언제든 모두 삭제할 수 있어요.",
  "Delete my account and data": "계정과 데이터 삭제",
  "Delete everything for good?": "모두 영구 삭제할까요?",
  "Your account, resume, matches and saved jobs will be removed. This can't be undone.":
    "계정, 이력서, 추천 결과, 저장한 공고가 삭제됩니다. 되돌릴 수 없어요.",
  "Yes, delete": "네, 삭제",
  Cancel: "취소",
  "Account deleted": "계정이 삭제되었어요",
  "Your resume and data are gone. Taking you to the login page…": "이력서와 데이터가 삭제되었어요. 로그인 페이지로 이동합니다…",

  // matches
  "Your top {n}": "나의 TOP {n}",
  "Matches for you": "맞춤 추천 공고",
  "best score": "최고 점수",
  "postings checked": "검토한 공고",
  "live in top list": "실시간 공고",
  "Upload your resume first": "먼저 이력서를 올려 주세요",
  "We need your skills to recommend postings.": "공고를 추천하려면 기술 정보가 필요해요.",
  "No postings match these filters. Try widening them.": "조건에 맞는 공고가 없어요. 필터를 넓혀 보세요.",
  "Skills {have}/{total} ({pct}%) · Text similarity {sim}": "기술 {have}/{total} ({pct}%) · 텍스트 유사도 {sim}",
  "You have": "보유",
  Missing: "부족",
  "Nothing — you have all required skills": "없음 — 필수 기술을 모두 갖췄어요",
  "Nice to have": "우대",
  "★ Saved": "★ 저장됨",
  "☆ Save": "☆ 저장",
  "How the score works": "점수 계산 방식",
  "Match = 100 × ({ws} × skill overlap + {wt} × text similarity). Skill overlap is the share of the posting's required skills that you have; text similarity compares your resume with the posting text ({backend}).":
    "매칭 점수 = 100 × ({ws} × 기술 일치율 + {wt} × 텍스트 유사도). 기술 일치율은 공고의 필수 기술 중 보유한 비율이고, 텍스트 유사도는 이력서와 공고 본문을 비교한 값이에요 ({backend}).",
  "Grow your matches": "추천 공고 늘리기",
  "Add one skill and see which postings would fit you better.": "기술 하나를 더하면 어떤 공고에 더 잘 맞는지 보여 드려요.",
  "+{n} strong matches": "강력 추천 +{n}",
  "+1 strong match": "강력 추천 +1",
  "1 posting scores higher": "공고 1개 점수 상승",
  "{n} postings score higher": "공고 {n}개 점수 상승",
  "I already have it": "이미 보유한 기술이에요",
  "Adding…": "추가 중…",
  "No suggestions: you already cover the required skills of these postings.":
    "추천할 기술이 없어요. 이 공고들의 필수 기술을 모두 갖췄어요.",
  "Strong match = score 70+.": "강력 추천 = 점수 70점 이상.",

  // filters & badges
  "Job type": "고용 형태",
  Any: "전체",
  Location: "지역",
  Anywhere: "전체 지역",
  "My Korean (TOPIK)": "내 한국어 (TOPIK)",
  "Show all": "모두 보기",
  "Korean not needed only": "한국어 불필요 공고만",
  "TOPIK {n}": "TOPIK {n}급",
  Internship: "인턴",
  "Full-time": "정규직",
  Seoul: "서울",
  Seongnam: "성남·판교",
  Daejeon: "대전",
  Busan: "부산",
  Incheon: "인천",
  Suwon: "수원",
  Ulsan: "울산",
  Jeju: "제주",
  Remote: "재택",
  "Korean not required": "한국어 불필요",
  "TOPIK {n}+": "TOPIK {n}급 이상",
  "est.": "추정",
  "The posting states this TOPIK level": "공고에 명시된 TOPIK 수준이에요",
  "Estimated: the posting does not state a TOPIK level": "추정치: 공고에 TOPIK 수준이 명시되지 않았어요",
  "Postings that need a higher Korean level than yours are hidden": "내 수준보다 높은 한국어가 필요한 공고는 숨겨요",

  // jobs, detail, saved
  "All postings": "전체 공고",
  "{n} found": "{n}건",
  Search: "검색",
  "Title, company or keyword": "직무, 회사 또는 키워드",
  Required: "필수",
  Preferred: "우대",
  "← Prev": "← 이전",
  "Next →": "다음 →",
  "← Back": "← 뒤로",
  "Skill overlap {pct}% · Text similarity {sim}": "기술 일치율 {pct}% · 텍스트 유사도 {sim}",
  "Nothing missing": "부족한 기술 없음",
  "Upload your resume to see your match score for this posting.": "이력서를 올리면 이 공고의 매칭 점수를 볼 수 있어요.",
  Description: "상세 내용",
  "Korean": "한국어",
  "Collected {date} · this is a snapshot, the original posting may have expired.":
    "수집일 {date} · 스냅샷이므로 원본 공고가 마감되었을 수 있어요.",
  "Original posting ↗": "원본 공고 ↗",
  "Saved postings": "저장한 공고",
  "Nothing saved yet.": "아직 저장한 공고가 없어요.",
  "Browse your matches and press ☆ Save.": "추천 공고에서 ☆ 저장을 눌러 보세요.",
  "saved {date}": "{date} 저장",
  Remove: "삭제",
};

const LangContext = createContext({ lang: "en", setLang: () => {} });
const KEY = "jobassist.lang";

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved) return saved;
    } catch {
      /* storage unavailable */
    }
    return navigator.language?.startsWith("ko") ? "ko" : "en";
  });
  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(KEY, lang);
    } catch {
      /* storage unavailable */
    }
  }, [lang]);
  return <LangContext.Provider value={{ lang, setLang }}>{children}</LangContext.Provider>;
}

export function useT() {
  const { lang, setLang } = useContext(LangContext);
  const t = (text, vars) => {
    const s = lang === "ko" ? KO[text] ?? text : text;
    return vars ? s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "") : s;
  };
  return { t, lang, setLang };
}
