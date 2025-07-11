# 사용자의 얼굴을 바라보며 대화하는 LLM 탑재 로봇

[Intel] 엣지 AI SW 아카데미 13기: 인텔 최종 프로젝트

Face Tracking 기능을 수행하고 LLM을 탑재하여 사용자와 대화를 할 수 있는 로봇을 구현하는 프로젝트입니다.

본 프로젝트에서 구현하고자 하는 기능은 다음과 같습니다.
* 사용자의 얼굴을 카메라로 감지하고, 사용자의 얼굴을 따라 로봇의 머리가 움직이는 동작을 수행합니다.
* 로봇에 장착된 마이크와 스피커를 통해 음성으로 대화를 주고받습니다.
* 로봇의 머리에 장착된 OLED로 로봇의 감정 상태를 표현합니다.
* (여유가 된다면 추가 기능을 탑재할 계획입니다.)

## High Level Design
### 프로젝트 아키텍처
- **전체 구조**
```
[USB-C PD 충전기]      [로봇 본체]                [로봇 머리]
전원 공급    →  STM32F411RE + ESP01  ←케이블→  ESP32-S3-CAM + 센서/액추에이터
                      
[라즈베리파이 4]    ←WiFi→  [로봇 시스템]
(별도 전원)
```
- **외부 처리**: 라즈베리파이 4 (AI 음성 대화, 별도 전원)
- **로봇 제어**: STM32F411RE (표정 애니메이션, 오디오 처리)
- **영상 처리**: ESP32-S3-CAM (Face Detection + 서보모터 제어)
- **무선 통신**: ESP01 WiFi 모듈 (라즈베리파이 ↔ STM32)
- **물리적 구조**: 몸통(전자부품) + 머리(ESP32-S3-CAM + 센서/액추에이터)
- **전원**: USB-C PD + DC-DC 변환 (로봇 전용), 라즈베리파이는 독립 전원

* (프로젝트 아키텍쳐 기술, 전반적인 diagram 으로 설명을 권장)
### 유스케이스 다이어그램

## Clone code

프로젝트를 clone하는 방법을 설명합니다.

```shell
git clone https://github.com/LES4975/my-little-chatbot.git
```

## Prerequite

* (프로잭트를 실행하기 위해 필요한 dependencies 및 configuration들이 있다면, 설치 및 설정 방법에 대해 기술)

```shell
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Steps to build

* (프로젝트를 실행을 위해 빌드 절차 기술)

```shell
cd ~/xxxx
source .venv/bin/activate

make
make install
```

## Steps to run

* (프로젝트 실행방법에 대해서 기술, 특별한 사용방법이 있다면 같이 기술)

```shell
cd ~/xxxx
source .venv/bin/activate

cd /path/to/repo/xxx/
python demo.py -i xxx -m yyy -d zzz
```

## Output

* (프로젝트 실행 화면 캡쳐)

![./result.jpg](./result.jpg)

## Appendix

* (참고 자료 및 알아두어야할 사항들 기술)

