# AWS MLA (Machine Learning Engineer – Associate)

> 사내 로컬 서버에서 LLM 서빙과 에이전트 환경을 구축하면서, **같은 일을 클라우드에서는 어떻게 설계하고 운영하는지** 궁금해졌습니다.
> 클라우드 기반 AI/LLM 파이프라인을 체계적으로 공부하려고 시작했고, **2026.12.23 시험**까지 과정을 블로그에 남기고 있습니다.

블로그 카테고리: [AWS MLA](https://blog.jimmy-home.com/@jaehwi?category=aws-mla#posts) · 시작 글: [MLA 공부 시작](https://blog.jimmy-home.com/@jaehwi/mla-01)

| # | 글 | 다루는 것 | 상태 |
|---|---|---|---|
| 00 | [데이터 형식](https://blog.jimmy-home.com/@jaehwi/mla-02) | Parquet, ORC, Avro, CSV / JSON, RecordIO-protobuf, File / Pipe / Fast File mode | 완료 |
| 01 | [저장소 (1)](https://blog.jimmy-home.com/@jaehwi/mla-03) | S3, S3 Glacier, EBS, EFS | 완료 |
| 01 | [저장소 (2)](https://blog.jimmy-home.com/@jaehwi/mla-04) | FSx, RDS, DynamoDB, Storage Gateway, DataSync | 작성 중 |

## 정리한 핵심

### 데이터 형식

| 형식 | 시험에서의 핵심 |
|---|---|
| Parquet | 컬럼 지향. **특정 컬럼만 읽어야 할 때** |
| ORC | 컬럼 기반, 대용량 분석. Parquet과 비슷 (Hive에서 출발) |
| Avro | row 기반. **스트리밍(Kafka)**, 레코드 단위로 계속 쓰는 작업, 스키마가 변하는 작업 |
| CSV / JSON | row 기반. 사람이 확인할 때. SageMaker 입력(CSV), Firehose 변환 입력(JSON) |
| RecordIO-protobuf | SageMaker 내장 알고리즘의 바이너리 형식. **희소 데이터, Factorization Machines**(Float32 tensor만) |
| File / Fast File / Pipe mode | 전체 다운로드 후 학습 / 필요할 때 스트리밍 / S3에서 FIFO로 스트리밍. 대용량이라 학습 시작이 느리면 Pipe |

### 저장소

| 서비스 | 시험에서의 핵심 |
|---|---|
| S3 | 학습 데이터의 기본 저장소. 접근 빈도와 성능에 맞춰 스토리지 클래스 선택. SageMaker 학습 입력은 같은 리전 |
| S3 Glacier | 가끔 쓰는 장기 보관. **얼마나 빨리 꺼내야 하느냐**로 클래스 선택 |
| EBS | IOPS가 중요하면 SSD, 처리량이 중요하면 HDD. 높은 지속 IOPS는 Provisioned IOPS(io1 / io2) |
| EFS | 여러 컴퓨트가 같은 파일을 공유, 용량 관리 없이 자동 확장 |
| FSx | 파일 시스템을 SageMaker 학습 입력으로 쓸 때는 EFS 또는 **FSx for Lustre** |
| RDS / DynamoDB | 정형(관계형) 데이터의 원천 / 키-값 · 문서 NoSQL 데이터의 원천 |
| Storage Gateway | 온프레미스 앱이 클라우드 스토리지를 로컬처럼 쓰는 하이브리드 |
| DataSync | 온프레미스나 다른 클라우드에서 S3 · EFS · FSx로 대량 이전 |

---

- [공부 기록 목록](../README.md)
