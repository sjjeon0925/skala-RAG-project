> 이전 설계 기록입니다. 현재 구현은 수정방안 설계서와 [README.md](README.md), [적용 기록](docs/implementation-notes.md)을 기준으로 합니다. 아래의 3편 제한·수정 범위·설정값은 현행 지침이 아닙니다.

# Development Guide

## 1. 프로젝트 목표

본 프로젝트는 데이터센터·클라우드 환경에서 KV Cache 용량 문제를 해결하는
**ITME와 CXL-PIM을 여러 관점에서 비교 평가하는 Multi-Agent + Agentic RAG 시스템**이다.

특정 기술의 우열이나 승자를 정하는 것이 목적이 아니다.

아래 4가지 관점에서 두 기술을 평가하고,
관점별 공통점, 차이, Trade-off를 정리하여 최종 평가 보고서를 생성한다.

- 기술 성숙도
- 시장성
- 이해관계자
- 데이터센터 적용성

최종 실행 결과로 실제 평가 보고서가 생성되어야 한다.

---

## 2. 비교 대상

- Technology A: ITME
- Technology B: CXL-PIM
- Domain: 데이터센터 · 클라우드

### 문제 정의

긴 Context와 많은 동시 요청으로 KV Cache가 커지면 GPU HBM 용량이 부족해질 수 있다.

KV Cache를 GPU 외부 메모리로 이동하면 저장 공간은 늘릴 수 있지만,
GPU와 외부 메모리 사이의 데이터 이동으로 인해 Latency와 Bandwidth 병목이 발생할 수 있다.

따라서 두 기술이 KV Cache 저장 공간을 어떻게 확장하고,
데이터 이동 문제를 어떤 방식으로 처리하는지를 중심으로 평가한다.

---

## 3. RAG 문서

RAG Corpus는 Doc Pool에서 아래 3개 논문을 사용한다.

### 핵심 문서

1. **ITME**
   - Inference Tiered Memory Expansion with Disaggregated CXL-Hybrid Memories
   - 비교 대상 A의 직접 근거

2. **CXL-PIM**
   - Scalable Processing-Near-Memory for 1M-Token LLM Inference:
     CXL-Enabled KV-Cache Management Beyond GPU Limits
   - 비교 대상 B의 직접 근거

### 보조 문서

3. **InfiniGen**
   - Efficient Generative Inference of Large Language Models with Dynamic KV Cache Management
   - GPU 외부 메모리 Offloading과 데이터 이동 병목을 확인하기 위한 참고 자료

InfiniGen은 세 번째 평가 대상이 아니다.

---

## 4. Retrieval 구성

### Embedding

- Dense Embedding: `multilingual-e5-base`
- Keyword Search: `BM25`
- Retrieval 방식: Hybrid Retrieval

영어 논문을 한국어 Query로 검색할 수 있어야 한다.

CXL, PIM, RDMA와 같이 정확한 기술명이나 약어 검색이 중요하기 때문에
Dense Retrieval과 BM25를 같이 사용한다.

### 문서 처리

PDF를 처리할 때 페이지 정보를 유지한다.

Chunk에는 최소한 아래 Metadata를 저장한다.

```python
{
    "technology": "",
    "document_id": "",
    "page": 0,
    "chunk_id": ""
}검색 결과를 Agent에 전달할 때 Chunk Text만 넘기지 않고
출처와 페이지 Metadata를 같이 전달한다.
Chunk Size, Overlap, Top-K 등은 실제 검색 결과를 확인하면서 조정한다.

5. Evidence 구조
Agent가 긴 글 하나를 State에 저장하기보다,
가능하면 근거 단위로 구조화해서 저장한다.
{    "evidence_id": "E01",    "technology": "ITME",    "perspective": "technical",    "claim": "",    "source": "",    "page": 0,    "experimental_condition": "",    "content": ""}특히 성능 수치가 포함된 경우에는 다음 정보를 같이 저장한다.

출처
페이지
실험 환경
비교 Baseline
출처를 확인할 수 없는 정량 수치는 최종 보고서의 주요 근거로 사용하지 않는다.

6. Agent 구성
6.1 Technical Research Agent
사용 도구

RAG
역할
원 논문에서 기술 관련 근거를 찾는다.
확인할 항목:

작동 원리
KV Cache 저장 위치
Attention 실행 위치
데이터 이동 경로
실험 환경
주요 성능 결과
비교 Baseline
한계점
출력
technical_evidence

6.2 TRL Evaluation Agent
사용 도구

technical_evidence
Web Search
중요
TRL Agent는 Vector DB를 직접 검색하지 않는다.
Technical Research Agent가 RAG를 통해 확보한 technical_evidence를 먼저 사용한다.
논문만으로 확인하기 어려운 아래 정보는 Web Search로 보완한다.

PoC
Prototype
실제 환경 검증
제품화
상용화
실제 도입 여부
공식 TRL이 공개되지 않은 경우 반드시 다음과 같이 표시한다.
공개 정보 기반 TRL 추정출력
trl_analysis

6.3 Market Evaluation Agent
사용 도구

RAG
필요 시 Web Search 보완
역할
기술의 시장성과 생태계를 평가한다.
확인할 항목:

제품화
실제 채택
관련 생태계
성장 요인
도입 장벽
출력
market_analysis

6.4 Stakeholder Evaluation Agent
사용 도구

Web Search
역할
기술과 관련된 이해관계자의 시각을 조사한다.
대상:

개발자
도입 기업
HW 업체
경쟁 기술 진영
산업계
Fact와 Opinion을 구분해서 저장한다.
출력
stakeholder_analysis

6.5 Domain Evaluation Agent
사용 도구

RAG
technical_evidence
역할
데이터센터·클라우드 환경에서 두 기술의 적용 특성을 평가한다.
평가 기준:

Capacity
HBM 절감
Latency
TTFT / TPOT (자료가 있는 경우)
Throughput
Bandwidth
Data Movement
Attention 실행 위치
Scalability
Infrastructure Cost
기존 GPU 서버 통합 난이도
논문별 실험 환경이 다르면 성능 수치를 그대로 비교하지 않는다.
출력
domain_analysis

6.6 Synthesis Agent
새로운 자료를 검색하지 않는다.
앞 단계의 결과를 받아 아래 내용을 정리한다.
{    "consensus": [],    "conflicts": [],    "tradeoffs": [],    "evidence_gaps": []}특정 기술을 추천하거나 승자를 결정하지 않는다.

6.7 Report Agent
새로운 검색을 하지 않는다.
State에 저장된 결과만 사용해서 최종 보고서를 생성한다.
State에 없는 사실을 임의로 추가하지 않는다.

7. Agent별 사용 도구 정리
Agent사용 방식기술 조사 AgentRAGTRL 평가 AgentTechnical Evidence + Web Search시장 평가 AgentRAG + 필요 시 Web Search이해관계자 평가 AgentWeb Search도메인 평가 AgentRAG + Technical Evidence평가 종합 AgentState보고서 AgentState

8. State Schema
class EvaluationState(TypedDict):    technologies: list    domain: str    technical_evidence: dict    trl_analysis: dict    market_analysis: dict    stakeholder_analysis: dict    domain_analysis: dict    missing_evidence: list    retry_count: int    max_retries: int    counter_evidence: dict    conflicts: list    synthesis: dict    references: list    final_report: str병렬 Agent State 관리
4개 평가 Agent는 같은 Key를 수정하지 않는다.
TRL Agent         → trl_analysis
Market Agent      → market_analysis
Stakeholder Agent → stakeholder_analysis
Domain Agent      → domain_analysis여러 Agent가 동시에 하나의 evaluation Key에 결과를 저장하지 않는다.
공통 Evidence나 Reference를 누적해야 하는 경우에는 reducer 사용을 고려한다.

9. Graph 흐름
START
  ↓
기술 · 도메인 입력
  ↓
Technical Research Agent (RAG)
  ↓
1차 Evidence 충분성 검사
  │
  ├─ 충분
  │    ↓
  │  Fan-out
  │    ├─ TRL Agent
  │    ├─ Market Agent
  │    ├─ Stakeholder Agent
  │    └─ Domain Agent
  │
  └─ 부족
       ↓
     retry_count < max_retries ?
       ├─ YES
       │    ↓
       │  Query Rewrite
       │    ↓
       │  Technical Research Agent
       │
       └─ NO
            ↓
          missing_evidence 기록
            ↓
          Fan-out

4개 평가 Agent
  ↓
Fan-in
  ↓
2차 Evidence 충분성 검사
  │
  ├─ 충분 ─────────────────┐
  │                        │
  └─ 부족                  │
       ↓                    │
     missing_evidence 기록  │
       └────────────────────┘
                ↓
Counter-Evidence 검증
  ↓
Conflict 분석
  ↓
Synthesis Agent
  ↓
Report Agent
  ↓
최종 평가 보고서
  ↓
END

10. 1차 Evidence 충분성 검사
Technical Research Agent가 아래 내용을 확보했는지 확인한다.

작동 원리
KV Cache 저장 위치
Attention 실행 위치
데이터 이동 경로
실험 환경
주요 성능 결과
비교 Baseline
한계점
출처
정량적인 성능 주장에는 출처와 실험 조건이 같이 있어야 한다.
근거가 부족하면 missing_evidence에 부족한 항목을 기록하고 Query Rewrite를 수행한다.

11. 재검색 종료 조건
재검색이 계속 반복되지 않도록 최대 횟수를 둔다.
초기값:
max_retries = 2retry_count = 0동작:
if evidence_is_sufficient:    go_to_fanout()elif retry_count < max_retries:    retry_count += 1    rewrite_query()    go_to_technical_research()else:    save_missing_evidence()    go_to_fanout()검색을 반복해도 찾지 못한 정보는 임의로 생성하지 않는다.

12. 2차 Evidence 충분성 검사
4개 평가 Agent의 실행이 끝난 뒤 Fan-in하고 다시 근거를 확인한다.
관점별 확인 항목:
TRL

개발 단계 판단 근거
Prototype / PoC 근거
상용화 또는 실제 적용 근거
Market

제품화
채택 사례
생태계
도입 장벽
Stakeholder

서로 다른 이해관계자의 의견
긍정적인 의견
우려 사항
Domain

Capacity
Latency
Throughput
Bandwidth
Data Movement
Cost
Scalability
2차 검사에서는 전체 Agent를 다시 실행하지 않는다.
부족한 내용은 missing_evidence에 저장하고
최종 보고서의 한계점에 반영한다.

13. Counter-Evidence 검증
각 평가에서 나온 주요 주장에 대해
반대되는 근거나 제약 조건이 있는지 추가로 확인한다.
필요에 따라 RAG 또는 Web Search를 사용할 수 있다.
예:
기존 Claim:
"CXL-PIM은 GPU와 외부 메모리 사이의 데이터 이동을 줄인다."

Counter Search:
"CXL-PIM limitation"
"CXL-PIM overhead"
"CXL-PIM bandwidth bottleneck"반대 근거가 확인되면 counter_evidence에 저장한다.
찾지 못한 경우 반대 근거를 임의로 생성하지 않는다.
공개된 반대 근거를 확인하지 못함으로 기록한다.

14. Conflict 분석
다음 항목에서 관점이나 근거가 충돌하는지 확인한다.

성능 향상 :left_right_arrow: 추가 비용
메모리 확장 :left_right_arrow: 데이터 이동량
연구 결과 :left_right_arrow: 실제 상용화 수준
개발자 의견 :left_right_arrow: 기업 입장
ITME 실험 조건 :left_right_arrow: CXL-PIM 실험 조건
특히 아래 조건을 확인한다.

Model
GPU
Batch Size
Context Length
Precision
Baseline
실험 조건이 충분히 다르면 두 논문의 성능 수치를 직접 비교하지 않는다.
이 경우:
직접 비교 어려움으로 기록하고 각 논문의 자체 Baseline 대비 결과를 중심으로 설명한다.

15. Report Agent 생성 규칙
Report Agent는 아래 규칙을 지킨다.

특정 기술을 추천하지 않는다.
Winner를 선정하지 않는다.
State에 없는 사실을 추가하지 않는다.
출처가 없는 성능 수치를 사용하지 않는다.
실험 조건이 다른 수치를 단순 비교하지 않는다.
공식 TRL이 아닌 경우 공개 정보 기반 추정이라고 표시한다.
Fact와 Opinion을 구분한다.
Evidence가 부족하면 정보 부족으로 남긴다.
Counter-Evidence를 숨기지 않는다.
실제 보고서에서 사용한 자료만 Reference에 포함한다.


16. 최종 보고서 구조
SUMMARY

1. 분석 배경 및 문제 정의
2. 평가 대상 기술 선정
3. 기술 개요

4. 다관점 평가
   4.1 기술 성숙도
   4.2 시장성
   4.3 이해관계자
   4.4 데이터센터·클라우드 적용성

5. 관점 간 종합 및 시사점
   5.1 공통적으로 확인된 내용
   5.2 관점에 따라 평가가 달라지는 부분
   5.3 주요 Trade-off
   5.4 종합 의견

6. 분석 한계 및 신뢰성 확보
   6.1 공개 정보 기반 분석의 한계
   6.2 실험 환경 차이에 따른 직접 비교 한계
   6.3 Evidence Gap
   6.4 확증편향 방지 방법

REFERENCE

17. 권장 디렉토리 구조
project/
├── data/
│   ├── raw/
│   └── vectorstore/
│
├── agents/
│   ├── technical.py
│   ├── trl.py
│   ├── market.py
│   ├── stakeholder.py
│   ├── domain.py
│   ├── synthesis.py
│   └── report.py
│
├── nodes/
│   ├── evidence_check.py
│   ├── query_rewrite.py
│   ├── counter_evidence.py
│   └── conflict.py
│
├── retrieval/
│   ├── loader.py
│   ├── chunker.py
│   ├── embedding.py
│   ├── bm25.py
│   └── retriever.py
│
├── graph/
│   ├── state.py
│   └── workflow.py
│
├── prompts/
├── outputs/
├── app.py
└── README.md

18. 개발 시 주의사항
아래 설계를 임의로 복잡하게 변경하지 않는다.
하지 말아야 할 것:

임의로 새로운 Agent 추가
2차 Evidence 검사에 새로운 재검색 Loop 추가
찾지 못한 정보를 LLM이 추측해서 채우기
ITME와 CXL-PIM의 단순 승패 결정
InfiniGen을 세 번째 평가 대상으로 사용
TRL Agent에서 별도의 RAG Retrieval 수행
병렬 Agent가 하나의 State Key를 동시에 수정
출처 Page 정보를 제거하고 Text만 저장
실험 조건이 다른 성능 수치를 그대로 순위 비교
가장 중요한 것은 복잡한 Graph를 만드는 것이 아니라,
코드를 실행했을 때 처음부터 끝까지 실제 평가 보고서가 생성되는 것이다.

AI Coding Instruction
아래 설계를 기준으로 구현한다.

State와 Graph 구조를 임의로 변경하지 않는다.
TRL Agent는 별도의 RAG 검색을 수행하지 않는다.
TRL Agent는 technical_evidence를 재사용하고 필요한 외부 정보만 Web Search로 보완한다.
모든 주요 평가 결과에는 가능한 경우 Evidence와 Source를 연결한다.
근거가 없는 사실을 생성하지 않는다.
특정 기술의 승자를 정하지 않는다.
실행 완료 시 ITME와 CXL-PIM의 다관점 평가 보고서가 실제 파일로 생성되어야 한다.