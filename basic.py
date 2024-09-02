import pandas as pd
import pygame
import tkinter as tk
from tkinter import messagebox
from typing import Dict
from pathlib import Path
import json
import os
import logging
import subprocess
import tempfile
import time
from PIL import Image, ImageTk


# 화면 설정
app_title = "천일문 기본"
WINDOW_SIZE = "1080x620"
BG_COLOR = "gray3"

EXCEL_FILE = Path("basic.xlsx")

# 단일음성 화면 폰트설정
FONT_SETTINGS_LABEL = ("NanumBarunGothic", 18, "bold")
FONT_SETTINGS_ENTRY = ("NanumBarunGothic", 15, "normal")
FONT_SETTINGS_BUTTON = ("NanumBarunGothic", 16, "bold")

# 폰트 설정
FONT_TOP = ("NanumBarunGothic", 30, "bold")
FONT_TOP2 = ("NanumBarunGothic", 70, "bold")
FONT_LANGUAGE = ("NanumBarunGothic", 30, "bold")
FONT_NO = ("NanumBarunGothic", 45, "bold")
FONT_KO = ("NanumBarunGothic", 60, "bold")
FONT_EN = ("Times New Roman", 65, "italic")
FONT_CH = ("PingFang SC", 50, "normal")
FONT_BOTTOM = ("NanumBarunGothic", 30, "bold")
FONT_BREAK = ("NanumBarunGothic", 120, "bold")
FONT_COUNTDOWN = ("NanumBarunGothic", 280, "bold")
FONT_START_BUTTON = ("NanumBarunGothic", 20, "bold")
FONT_END_BUTTON = ("NanumBarunGothic", 20, "bold")
FONT_START_LABEL = ("NanumBarunGothic", 35, "bold")
FONT_END_LABEL = ("NanumBarunGothic", 35, "bold")

# 레이아웃 설정
LAYOUT_SETTINGS = {
    'INITIAL_SCREEN': {
        'TITLE_PADDING': 30,
        'INPUT_FRAME_PADDING': 10,
        'LANGUAGE_OPTIONS_PADDING': 10,
        'START_BUTTON_PADDING': 10,
        'BOTTOM_LABEL_PADDING': 10,
    },
}

# 시간 관련 설정 (모든 시간은 밀리초 단위)

GENERAL_SETTINGS = {
    'BREAK_TIME': 6000,
    'FINAL_MESSAGE_DISPLAY_TIME': 13000,
    'COUNTDOWN_INTERVAL': 1000,
    'COUNTDOWN_START': 3,
}

# 파일 경로 설정
AUDIO_KO = "sound_ko/ko{}.wav"
AUDIO_EN = "sound_en/en{}.wav"
AUDIO_CH = "sound_ch/ch{}.wav"
SOUND_DRUM = Path("../drum.mp3")
COUNTDOWN_AUDIO = Path("../countdown_audio.wav")
CONFIG_FILE = Path(os.path.expanduser("~")) / ".conversation_app_config.json"

# 로깅 설정
log_file = Path("../conversation_app.log")
logging.basicConfig(
    level=logging.INFO,  # DEBUG에서 INFO로 변경
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=str(log_file),
    filemode='a'
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


class AudioManager:
    LANG_SETTINGS = {
        "한국어": {'font': FONT_KO, 'fg': "white"},
        "영어": {'font': FONT_EN, 'fg': "yellow"},
        "중국어": {'font': FONT_CH, 'fg': "white"}
    }
    LANGUAGE_CODES = {
        "한국어": "KO",
        "영어": "EN",
        "중국어": "CH"
    }

    def __init__(self):
        pygame.mixer.init()
        self.sounds = {
            "drum": pygame.mixer.Sound(str(SOUND_DRUM)),
            "final": pygame.mixer.Sound("../final.MP3")
        }
        self.temp_dir = tempfile.mkdtemp()

    def play_sound(self, sound_name: str):
        try:
            self.sounds[sound_name].play()
        except pygame.error as e:
            logging.error(f"Error playing sound {sound_name}: {e}")

    @staticmethod
    def play_audio_file(file_path: str):
        try:
            sound = pygame.mixer.Sound(file_path)
            sound.play()
        except pygame.error as e:
            logging.error(f"Error playing audio file {file_path}: {e}")

    def get_audio_length(self, sentence_number: int, language: str) -> float:
        lang_code = self.get_language_code(language)
        audio_file = globals()[f"AUDIO_{lang_code}"].format(sentence_number)
        try:
            if not os.path.exists(audio_file):
                logging.warning(f"Audio file not found: {audio_file}")
                return 2.0  # 파일이 없을 경우 기본값 반환
            return pygame.mixer.Sound(audio_file).get_length()
        except pygame.error:
            logging.error(f"Error getting length of audio for sentence {sentence_number} in {language}")
            return 2.0  # 오류 발생 시 기본값 반환

    def play_sentence_audio(self, sentence_number: int, language: str, speed: float = 1.0):
        try:
            lang_code = self.get_language_code(language)
            audio_file = globals()[f"AUDIO_{lang_code}"].format(sentence_number)

            if not Path(audio_file).exists():
                raise FileNotFoundError(f"{audio_file} not found")

            if speed != 1.0:
                temp_output = os.path.join(self.temp_dir, f"temp_output_{sentence_number}_{language}.mp3")
                self.change_audio_speed(audio_file, temp_output, speed)
                audio_file = temp_output

            sound = pygame.mixer.Sound(audio_file)
            sound.play()

            # 재생이 끝날 때까지 대기
            pygame.time.wait(int(sound.get_length() * 1000 / speed))

            # logging.info(f"Finished audio No.{sentence_number} in {language}")

        except Exception as e:
            logging.error(f"Error playing audio for sentence {sentence_number} in {language}: {e}")
            print(f"Error playing audio: {e}")

    @staticmethod
    def change_audio_speed(input_file, output_file, speed):
        try:
            command = [
                'ffmpeg',
                '-i', input_file,
                '-filter:a', f'atempo={speed}',
                '-vn',
                output_file
            ]
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logging.info(f"Audio speed changed successfully. FFmpeg output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error changing audio speed: {e}")
            logging.error(f"FFmpeg error output: {e.stderr}")
            return False

    @staticmethod
    def check_ffmpeg():
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            logging.info(f"ffmpeg version: {result.stdout.split('\\n')[0]}")
        except FileNotFoundError:
            logging.error("ffmpeg not found. Please install ffmpeg and add it to your PATH.")
            print("Error: ffmpeg not found. Please install ffmpeg and add it to your PATH.")

    def get_language_code(self, language: str) -> str:
        return self.LANGUAGE_CODES.get(language, language)

    def __del__(self):
        # 임시 디렉토리 삭제
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)


class DataManager:
    def __init__(self):
        try:
            self.data = pd.read_excel(EXCEL_FILE, header=None, names=["한국어", "영어", "중국어"])
            logging.info(f"Loaded {len(self.data)} sentences")
        except FileNotFoundError:
            logging.error(f"Error: Excel file not found at {EXCEL_FILE}")
            self.data = pd.DataFrame(columns=["한국어", "영어", "중국어"])

    def get_sentence(self, index: int) -> Dict[str, str]:
        if 0 <= index < len(self.data):
            sentence = self.data.iloc[index].to_dict()
            logging.debug(f"Retrieved sentence {index}: {sentence}")
            return sentence
        else:
            logging.warning(f"Index {index} is out of range")
            return {"한국어": "", "영어": "", "중국어": ""}


class ConversationApp(tk.Tk):
    LANG_SETTINGS = {
        "한국어": {'font': FONT_KO, 'fg': "white", 'initial_size': 55, 'min_size': 30},
        "영어": {'font': FONT_EN, 'fg': "yellow", 'initial_size': 70, 'min_size': 35},
        "중국어": {'font': FONT_CH, 'fg': "white", 'initial_size': 55, 'min_size': 30}
    }

    # 디폴트 값 설정
    default_delays = {
        'korean_subtitle_delay': 0,
        'english_subtitle_delay': 0,
        'english_audio_delay': 0,  # 이 줄을 추가
        'chinese_subtitle_delay': 0,
        'next_sentence_delay': 1
    }

    DEFAULT_SETTINGS = {
        'start_sentence': 1,
        'end_sentence': 100,
        'audio_speed': 2.0,
        'show_english_chinese_simultaneously': True,
        'show_한국어': True,
        'show_영어': True,
        'show_중국어': True,
        'play_한국어': False,
        'play_영어': True,
        'play_중국어': False
    }

    def __init__(self):
        super().__init__()
        logging.info("ConversationApp 초기화 중")

        self.title(app_title)
        self.geometry(WINDOW_SIZE)
        self.configure(bg=BG_COLOR)

        # 여기에 모든 인스턴스 속성을 초기화합니다
        self.audio_manager = AudioManager()
        self.data_manager = DataManager()
        self.message_label = None  # message_label을 여기서 초기화
        self.countdown_label = None

        # DoubleVar 객체 먼저 초기화
        self.initial_korean_speed = tk.DoubleVar(self, value=2.0)
        self.initial_english_speed = tk.DoubleVar(self, value=2.0)
        self.korean_audio_speed = tk.DoubleVar(self, value=2.0)
        self.english_audio_speed = tk.DoubleVar(self, value=2.0)

        # 화면 크기에 따른 동적 설정
        self.update_idletasks()  # 윈도우 크기 정보 업데이트
        self.screen_width = self.winfo_width()
        self.screen_height = self.winfo_height()

        self.initial_font_sizes = {lang: settings['initial_size'] for lang, settings in self.LANG_SETTINGS.items()}

        # 동적으로 계산된 레이아웃 설정
        self.DYNAMIC_LAYOUT = {
            'TITLE_FONT_SIZE': int(self.screen_height * 0.1),
            'INPUT_FONT_SIZE': int(self.screen_height * 0.05),
            'BUTTON_FONT_SIZE': int(self.screen_height * 0.03),
            'PADDING': int(self.screen_height * 0.02),
        }

        # 메인 프레임 초기화
        self.main_frame = None
        self.lang_frame = None
        self.lang_labels = {}

        self.prepared_subtitles = {}

        # 한영 동시 자막 옵션 추가
        self.show_english_chinese_simultaneously = tk.BooleanVar(value=True)
        self.audio_languages = []
        self.start_time = 0

        self.korean_subtitle_delay = tk.DoubleVar(self, value=self.default_delays['korean_subtitle_delay'])
        self.english_audio_delay = tk.DoubleVar(self, value=self.default_delays['english_audio_delay'])
        self.english_subtitle_delay = tk.DoubleVar(self, value=self.default_delays['english_subtitle_delay'])
        self.chinese_subtitle_delay = tk.DoubleVar(self, value=self.default_delays['chinese_subtitle_delay'])
        self.next_sentence_delay = tk.DoubleVar(self, value=self.default_delays['next_sentence_delay'])

        self.data_manager = DataManager()
        # 한국어와 영어 음성 속도를 위한 별도의 변수
        self.korean_audio_speed = tk.DoubleVar(self, value=2.0)
        self.english_audio_speed = tk.DoubleVar(self, value=2.0)
        self.audio_speed = tk.DoubleVar(self, value=2.0)

        self.display_duration = tk.DoubleVar(self, value=1.0)

        self.current_sentence = 0
        self.start_sentence = tk.StringVar(value="1")
        self.end_sentence = tk.StringVar(value="100")
        self.end = 0

        self.language_vars = {lang: tk.BooleanVar(value=True) for lang in ["한국어", "영어", "중국어"]}
        self.audio_vars = {lang: tk.BooleanVar(value=False) for lang in ["한국어", "영어", "중국어"]}
        self.audio_vars["영어"].set(True)

        self.sentence_label = None
        # 카운트다운 관련 변수들
        self.countdown_label = None
        self.message_label = None
        self.countdown_value = GENERAL_SETTINGS['COUNTDOWN_START']

        self.korean_subtitle_entry = None
        self.english_audio_entry = None
        self.english_subtitle_entry = None
        self.next_sentence_entry = None
        self.texts = {"Korean": "", "English": "", "Chinese": ""}

        # Define constants
        self.BG_COLOR = "gray3"
        self.FONT_BREAK = ("NanumBarunGothic", 120, "bold")
        self.FONT_COUNTDOWN = ("NanumBarunGothic", 30, "bold")
        self.GENERAL_SETTINGS = {
            'BREAK_TIME': 8000,
            'FINAL_MESSAGE_DISPLAY_TIME': 20000,
            'FINAL_MESSAGE_EXTRA_DELAY': 1000,  # 1 -second delay after countdown
        }

        self.is_paused = False
        self.pause_time = 0
        self.pause_button = None

        # 음성 재생 상태를 추적하기 위한 변수 추가
        self.playing_korean = False
        self.playing_english = False
        # 초기 음성 속도를 저장할 변수 추가
        self.initial_korean_speed = tk.DoubleVar(self, value=2.0)
        self.initial_english_speed = tk.DoubleVar(self, value=2.0)

        # DoubleVar 객체 올바르게 초기화
        self.initial_korean_speed = tk.DoubleVar(self, value=2.0)
        self.initial_english_speed = tk.DoubleVar(self, value=2.0)
        self.korean_audio_speed = tk.DoubleVar(self, value=2.0)
        self.english_audio_speed = tk.DoubleVar(self, value=2.0)

        self.load_settings()
        self.last_adjusted_sentence = 0

        self.qr_image = None
        self._initialize_qr_code()

        self.create_initial_widgets()
        logging.info("초기 위젯 생성됨")
        self.update_speed_display()  # 초기 디스플레이 업데이트
        self.audio_manager.play_sound("drum")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        logging.info("ConversationApp 초기화 완료")

    def create_initial_widgets(self):
        # 초기 화면의 위젯들을 생성하는 메서드
        self._create_title_label()
        self._create_input_frame()
        self._create_language_options()
        self._create_start_button()
        self._create_delay_settings()
        self._create_speed_sliders()
        self._create_bottom_label()

    def _initialize_qr_code(self):
        qr_image_path = os.path.join("..", "qrcode.jpg")
        if os.path.exists(qr_image_path):
            logging.info(f"QR 코드 이미지 파일 확인됨: {qr_image_path}")
            self.qr_image_path = qr_image_path
        else:
            logging.warning(f"QR 코드 이미지 파일을 찾을 수 없습니다: {qr_image_path}")
            self.qr_image_path = None

    def add_qr_code(self, parent_frame):
        if self.qr_image_path:
            try:
                img = Image.open(self.qr_image_path)
                img = img.resize((100, 100))  # Basic resize without specifying method
                photo = ImageTk.PhotoImage(img)
                qr_label = tk.Label(parent_frame, bg=self.BG_COLOR)
                qr_label.image = photo  # Keep a reference!
                qr_label.configure(image=photo)
                qr_label.pack(side=tk.LEFT)
                logging.info("QR 코드 이미지가 성공적으로 표시되었습니다.")
            except Exception as e:
                logging.error(f"QR 코드 이미지 표시 중 오류 발생: {e}")
        else:
            logging.warning("QR 코드 이미지를 표시할 수 없습니다.")

    def add_message_and_qr(self, parent_frame):
        message_frame = tk.Frame(parent_frame, bg=self.BG_COLOR)
        message_frame.pack(side=tk.BOTTOM, pady=20)

        message_label = tk.Label(message_frame, text="이 영상은 몸에 좋은 WAV 파일로 녹화했습니다.",
                                 font=("NanumBarunGothic", 16), fg="white", bg=self.BG_COLOR)
        message_label.pack(side=tk.LEFT, padx=(0, 20))

        self.add_qr_code(message_frame)

    def show_final_message(self):
        for widget in self.winfo_children():
            widget.destroy()

        final_frame = tk.Frame(self, bg=self.BG_COLOR)
        final_frame.pack(expand=True, fill="both")

        # 전체 내용을 담을 중앙 프레임
        center_frame = tk.Frame(final_frame, bg=self.BG_COLOR)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # "Good Job!" 라벨과 카운트다운 라벨을 위한 프레임
        good_job_countdown_frame = tk.Frame(center_frame, bg=self.BG_COLOR)
        good_job_countdown_frame.pack()

        # "Good Job!" 라벨
        good_job_label = tk.Label(good_job_countdown_frame, text="Good Job!", font=self.FONT_BREAK, fg="white",
                                  bg=self.BG_COLOR)
        good_job_label.pack(side=tk.LEFT, padx=(0, 20))

        # 카운트다운 라벨
        countdown_label = tk.Label(good_job_countdown_frame, text="", font=self.FONT_COUNTDOWN, fg="yellow",
                                   bg=self.BG_COLOR)
        countdown_label.pack(side=tk.LEFT)

        # 메시지와 QR 코드를 위한 프레임
        message_qr_frame = tk.Frame(center_frame, bg=self.BG_COLOR)
        message_qr_frame.pack(pady=(20, 0))  # Good Job! 아래에 약간의 간격을 줍니다.

        # 메시지 라벨
        message_label = tk.Label(message_qr_frame, text="몸에 좋은 소리 mbc 다큐 영상 -->>",
                                 font=("NanumBarunGothic", 40), fg="hot pink", bg=self.BG_COLOR)
        message_label.pack(side=tk.LEFT, padx=(0, 20))

        # QR 코드 추가
        self.add_qr_code(message_qr_frame)

        self.update()

        self.play_final_sound()

        def update_countdown(remaining):
            if remaining > 0:
                countdown_label.config(text=f"{remaining}")
                self.after(1000, update_countdown, remaining - 1)
            else:
                countdown_label.config(text="0")  # 카운트다운 종료 시 0 표시
                self.after(self.GENERAL_SETTINGS['FINAL_MESSAGE_EXTRA_DELAY'], self.finish_application)

        update_countdown(self.GENERAL_SETTINGS['FINAL_MESSAGE_DISPLAY_TIME'] // 1000)

    def show_countdown(self):
        for widget in self.winfo_children():
            widget.destroy()

        countdown_frame = tk.Frame(self, bg=BG_COLOR)
        countdown_frame.pack(expand=True, fill="both")

        # 숫자를 위한 프레임 (화면의 중앙에 위치)
        number_frame = tk.Frame(countdown_frame, bg=BG_COLOR)
        number_frame.place(relx=0.5, rely=0.42, anchor="center", relwidth=1, relheight=0.5)

        self.countdown_label = tk.Label(number_frame, text="", font=FONT_COUNTDOWN, fg="white", bg=BG_COLOR)
        self.countdown_label.place(relx=0.5, rely=0.5, anchor="center")

        # 메시지를 위한 프레임 (화면의 아래쪽에 위치)
        message_frame = tk.Frame(countdown_frame, bg=BG_COLOR)
        message_frame.place(relx=0.5, rely=0.75, anchor="center", relwidth=1, relheight=0.3)

        self.message_label = tk.Label(message_frame,
                                      text="",
                                      font=("NanumBarunGothic", 63),  # 폰트 크기를 줄임
                                      fg="hot pink",
                                      bg=BG_COLOR,
                                      wraplength=900,  # wraplength를 증가
                                      justify="center")
        self.message_label.place(relx=0.5, rely=0.5, anchor="center")

        self.countdown_value = GENERAL_SETTINGS['COUNTDOWN_START']

        self.play_countdown_message()
        self.type_message("이 영상은 몸에 좋은 WAV 파일로 녹화했습니다.")

        self.update_countdown()

    def type_message(self, message, index=0):
        if index < len(message):
            self.message_label.config(text=message[:index + 1])
            self.after(95, self.type_message, message, index + 1)

    def update_countdown(self):
        if self.countdown_value > 0:
            self.countdown_label.config(text=str(self.countdown_value))
            self.countdown_value -= 1
            self.after(GENERAL_SETTINGS['COUNTDOWN_INTERVAL'], self.update_countdown)
        else:
            self.finish_countdown()

    def play_countdown_message(self):
        if COUNTDOWN_AUDIO.exists():
            self.audio_manager.play_audio_file(str(COUNTDOWN_AUDIO))
        else:
            print(f"Error: Countdown audio file not found at {COUNTDOWN_AUDIO}")

    def setup_conversation_screen(self):
        # logging.info("대화 화면 설정 중")

        # 기존의 모든 위젯 제거
        for widget in self.winfo_children():
            widget.destroy()

        # 메인 프레임 생성
        self.main_frame = tk.Frame(self, bg=BG_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 상단 프레임 (타이틀 및 문장 번호)
        self._create_top_frame()

        # 중앙 프레임 (자막)
        self._create_language_frame(initialize_empty=True)

        # 하단 프레임 (버튼 등)
        self._create_bottom_frame()

        self.update_idletasks()
        self.update()
        logging.info("대화 화면 설정 완료")

    def toggle_pause_resume(self):
        if self.is_paused:
            self.resume_conversation()
        else:
            self.pause_conversation()

    def pause_conversation(self):
        if not self.is_paused:
            self.is_paused = True
            self.pause_time = time.time()
            self.pause_button.config(text="Resume")
            logging.info("대화 일시 정지")

    def resume_conversation(self):
        if self.is_paused:
            self.is_paused = False
            pause_duration = time.time() - self.pause_time
            self.start_time += pause_duration
            self.pause_button.config(text="Pause")
            logging.info(f"대화 재개 (정지 시간: {pause_duration:.2f}초)")

            # 현재 진행 중이던 작업 재개
            self.play_audio_and_show_subtitles(self.audio_languages)

    def _create_speed_sliders(self):
        speed_frame = tk.Frame(self, bg=BG_COLOR)
        speed_frame.pack(pady=10)

        # 한국어 음성 속도 슬라이더
        tk.Label(speed_frame, text="한국어:", font=FONT_LANGUAGE, fg="white", bg=BG_COLOR).pack(side=tk.LEFT, padx=(0, 10))
        tk.Scale(speed_frame, from_=1.0, to=4.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.initial_korean_speed, length=150, font=FONT_SETTINGS_ENTRY,
                 fg="white", bg="gray20", troughcolor="gray40", highlightthickness=0,
                 command=self.on_speed_change).pack(side=tk.LEFT, padx=(0, 20))

        # 영어 음성 속도 슬라이더
        tk.Label(speed_frame, text="영어:", font=FONT_LANGUAGE, fg="white", bg=BG_COLOR).pack(side=tk.LEFT, padx=(0, 10))
        tk.Scale(speed_frame, from_=1.0, to=4.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.initial_english_speed, length=150, font=FONT_SETTINGS_ENTRY,
                 fg="white", bg="gray20", troughcolor="gray40", highlightthickness=0,
                 command=self.on_speed_change).pack(side=tk.LEFT)

    def update_speed_display(self):
        display_parts = [f"{app_title} {self.end_sentence.get()}"]  # 수정된 부분

        if self.audio_vars["한국어"].get():
            korean_speed = self.initial_korean_speed.get()
            display_parts.append(f"한글{korean_speed:.1f}배")

        if self.audio_vars["영어"].get():
            english_speed = self.initial_english_speed.get()
            display_parts.append(f"영어{english_speed:.1f}배")

        display_text = " | ".join(display_parts)

        if hasattr(self, 'title_speed_label') and self.title_speed_label.winfo_exists():
            self.title_speed_label.config(text=display_text)
        else:
            logging.info(f"Speed display updated: {display_text}")

    def on_speed_change(self, _):
        self.save_settings()
        self.update_speed_display()

    def start_conversation(self):
        logging.info("Starting conversation")
        try:
            start = int(self.start_sentence.get())
            end = int(self.end_sentence.get())

            self.save_settings()

            # 현재 설정된 속도를 오디오 재생 속도로 설정
            self.korean_audio_speed.set(self.initial_korean_speed.get())
            self.english_audio_speed.set(self.initial_english_speed.get())

            for widget in self.winfo_children():
                widget.destroy()
            logging.info("All widgets destroyed")

            self.current_sentence = start
            self.end = end

            # 자막 미리 준비
            self.prepare_subtitles(start, end)

            self.setup_conversation_screen()
            self.update_speed_display()  # 대화 시작 시 배속 정보 업데이트
            logging.info("Conversation screen setup completed")

            self.show_countdown()
            logging.info("Countdown started")

        except ValueError:
            logging.error("Invalid input for start or end sentence")
            messagebox.showerror("입력 오류", "시작과 끝 문장 번호는 숫자여야 합니다.")

        logging.info("Start conversation method completed")

    def update_audio_settings(self):
        logging.info("Updating audio settings")
        selected_languages = [lang for lang in ["한국어", "영어", "중국어"] if self.audio_vars[lang].get()]

        if len(selected_languages) > 1:
            logging.info("Multiple languages selected for audio")
        else:
            logging.info(f"Single language selected for audio: {selected_languages[0] if selected_languages else 'None'}")

        self.update_speed_display()  # 오디오 설정이 변경될 때마다 속도 디스플레이 업데이트
        self.save_settings()

    def _create_delay_settings(self):
        delay_frame = tk.Frame(self, bg=BG_COLOR)
        delay_frame.pack(pady=10)

        self.korean_subtitle_entry = self._create_delay_input(
            parent=delay_frame,
            text="한글 자막 :",
            variable=self.korean_subtitle_delay
        )

        self.english_subtitle_entry = self._create_delay_input(
            parent=delay_frame,
            text="영어 자막 :",
            variable=self.english_subtitle_delay
        )

        self.english_audio_delay_entry = self._create_delay_input(
            parent=delay_frame,
            text="영어 음성 :",
            variable=self.english_audio_delay
        )

        self.next_sentence_entry = self._create_delay_input(
            parent=delay_frame,
            text="다음 문장 :",
            variable=self.next_sentence_delay
        )

    def _create_delay_input(self, parent, text, variable):
        frame = tk.Frame(parent, bg=BG_COLOR)
        frame.pack(side=tk.LEFT, padx=6)

        tk.Label(frame, text=text, font=FONT_SETTINGS_LABEL, fg="white", bg=BG_COLOR, width=7, anchor='e').pack(
            side=tk.LEFT, padx=(0, 2))

        vcmd = (self.register(self._validate_float), '%P')
        entry = tk.Entry(frame, textvariable=variable, font=FONT_SETTINGS_ENTRY, width=3, validate="key",
                         validatecommand=vcmd)
        entry.pack(side=tk.LEFT)
        entry.insert(0, str(variable.get()))
        entry.bind("<FocusOut>", self.on_delay_change)  # 포커스가 빠져나갈 때 설정 저장

        tk.Label(frame, text="초", font=FONT_SETTINGS_LABEL, fg="white", bg=BG_COLOR).pack(side=tk.LEFT, padx=(3, 0))

        return entry

    @staticmethod
    def _validate_float(value):
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False

    def on_delay_change(self, _):
        self.save_settings()

    def on_duration_change(self, value):
        logging.info(f"Display duration changed to {value}")
        self.save_settings()

    def _create_title_label(self):
        tk.Label(self, text=app_title, font=FONT_TOP2, fg="yellow", bg=BG_COLOR).pack(
            pady=LAYOUT_SETTINGS['INITIAL_SCREEN']['TITLE_PADDING'])

    def _create_input_frame(self):
        input_frame = tk.Frame(self, bg=BG_COLOR)
        input_frame.pack(pady=LAYOUT_SETTINGS['INITIAL_SCREEN']['INPUT_FRAME_PADDING'])

        self._create_start_entry(input_frame)
        self._create_end_entry(input_frame)

    def _create_start_entry(self, parent):
        tk.Label(parent, text="시작:", font=FONT_START_LABEL, fg="white", bg=BG_COLOR).grid(row=0, column=0, padx=10)
        start_entry = tk.Entry(parent, textvariable=self.start_sentence, font=FONT_LANGUAGE, width=4,
                               fg="white", bg=BG_COLOR, insertbackground="white", justify="center")
        start_entry.grid(row=0, column=1, padx=10)
        start_entry.focus_set()
        start_entry.bind("<Return>", self.focus_end_entry)

    def _create_end_entry(self, parent):
        tk.Label(parent, text="끝:", font=FONT_END_LABEL, fg="white", bg=BG_COLOR).grid(row=0, column=2, padx=10)
        end_entry = tk.Entry(parent, textvariable=self.end_sentence, font=FONT_LANGUAGE, width=4, fg="white",
                             bg=BG_COLOR, insertbackground="white", justify="center")
        end_entry.grid(row=0, column=3, padx=10)
        end_entry.bind("<Return>", self.start_conversation_from_entry)

    def _create_language_options(self):
        tk.Label(self, text="[ 언어/음성 ]", font=FONT_LANGUAGE, fg="white", bg=BG_COLOR).pack(
            pady=LAYOUT_SETTINGS['INITIAL_SCREEN']['LANGUAGE_OPTIONS_PADDING'])

        options_frame = tk.Frame(self, bg=BG_COLOR)
        options_frame.pack(pady=10)

        for i, lang in enumerate(["한국어", "영어", "중국어"]):
            self._create_language_checkbox(options_frame, lang, i)
            self._create_audio_checkbox(options_frame, lang, i)

        # 영중자막 라벨
        tk.Label(options_frame, text="영중 자막", font=FONT_LANGUAGE, fg="white", bg=BG_COLOR).grid(row=0, column=5,
                                                                                                padx=(10, 0))

        # 영중자막 체크박스 프레임
        simultaneous_frame = tk.Frame(options_frame, bg=BG_COLOR)
        simultaneous_frame.grid(row=1, column=5, padx=(10, 0))

        # '동시' 문구 추가
        tk.Label(simultaneous_frame, text="동시", font=FONT_LANGUAGE, fg="white", bg=BG_COLOR).pack(side=tk.LEFT,
                                                                                                  padx=(0, 5))

        # 영중자막 체크박스
        simultaneous_cb = tk.Checkbutton(simultaneous_frame, text="",
                                         variable=self.show_english_chinese_simultaneously,
                                         font=FONT_LANGUAGE, fg="white", bg=BG_COLOR, selectcolor=BG_COLOR,
                                         command=self.on_simultaneous_change)
        simultaneous_cb.pack(side=tk.LEFT)

    def on_simultaneous_change(self):
        self.save_settings()

    def _create_language_checkbox(self, parent, lang, column):
        cb = tk.Checkbutton(parent, text=lang, variable=self.language_vars[lang], font=FONT_LANGUAGE,
                            fg="white", bg=BG_COLOR, selectcolor=BG_COLOR,
                            command=lambda language=lang: self.on_language_toggle(language))
        cb.grid(row=0, column=column, padx=20)

    def _create_audio_checkbox(self, parent, lang, column):
        cb = tk.Checkbutton(parent, text="음성", variable=self.audio_vars[lang],
                            font=FONT_LANGUAGE, fg="white", bg=BG_COLOR, selectcolor=BG_COLOR,
                            command=self.update_audio_settings)
        cb.grid(row=1, column=column, padx=20)

    def _create_start_button(self):
        tk.Button(self, text="시작", command=self.start_conversation, font=FONT_LANGUAGE, fg="black",
                  bg=BG_COLOR).pack(pady=LAYOUT_SETTINGS['INITIAL_SCREEN']['START_BUTTON_PADDING'])

    def _create_bottom_label(self):
        tk.Label(self, text="한글속청 30일 영어 귀가 뚫린다!", font=FONT_BOTTOM, fg="yellow", bg=BG_COLOR).pack(
            side=tk.BOTTOM, pady=LAYOUT_SETTINGS['INITIAL_SCREEN']['BOTTOM_LABEL_PADDING'])

    def on_language_toggle(self, lang: str):
        print(f"{lang} is now {'active' if self.language_vars[lang].get() else 'inactive'}")
        if not self.language_vars[lang].get():
            self.audio_vars[lang].set(False)

    def focus_end_entry(self, _):
        self.focus_get().tk_focusNext().focus()
        return "break"

    def start_conversation_from_entry(self, _):
        self.start_conversation()
        return "break"

    def prepare_subtitles(self, start_sentence, end_sentence):
        self.prepared_subtitles = {}
        for i in range(start_sentence, end_sentence + 1):
            sentence = self.data_manager.get_sentence(i - 1)
            self.prepared_subtitles[i] = {
                "한국어": self.split_korean_text(sentence["한국어"]),
                "영어": self.split_english_text(sentence["영어"]),
                "중국어": sentence["중국어"]
            }
        logging.info(f"Prepared subtitles for sentences {start_sentence} to {end_sentence}")

    def finish_countdown(self):
        # 카운트다운 종료 후 대화 화면으로 전환
        self.setup_conversation_screen()
        self.after(1000, self.next_sentence)

    def adjust_frame_size(self):
        # logging.info(f"No.{self.current_sentence}, Adjusting frame size")
        if not hasattr(self, 'lang_frame') or not self.lang_labels:
            logging.warning("Language frame or labels not initialized. Skipping frame size adjustment.")
            return

        available_height = self.lang_frame.winfo_height()
        total_content_height = 0
        current_font_sizes = {}

        # 먼저 모든 라벨을 초기 폰트 크기로 재설정
        for lang, label in self.lang_labels.items():
            initial_size = self.LANG_SETTINGS[lang]['initial_size']
            initial_font = (self.LANG_SETTINGS[lang]['font'][0], initial_size, self.LANG_SETTINGS[lang]['font'][2])
            label.config(font=initial_font)
            current_font_sizes[lang] = initial_size

            self.lang_frame.update_idletasks()

        # 초기 크기로 설정된 후의 전체 내용 높이 계산
        for label in self.lang_labels.values():
            total_content_height += label.winfo_reqheight()

        all_single_line = all(len(label.cget("text").split('\n')) == 1 for label in self.lang_labels.values())
        padding = 7 if all_single_line else 3

        for label in self.lang_labels.values():
            label.pack_configure(pady=padding)

        # 높이 조정이 필요한 경우에만 폰트 크기 조정
        if total_content_height > available_height:
            scale_factor = available_height / total_content_height
            scale_factor = max(scale_factor, 0.85)  # 최대 15%까지만 축소

            for lang, label in self.lang_labels.items():
                current_size = current_font_sizes[lang]
                new_size = max(int(current_size * scale_factor), self.LANG_SETTINGS[lang]['min_size'])

                if new_size < current_size:
                    new_font = (self.LANG_SETTINGS[lang]['font'][0], new_size, self.LANG_SETTINGS[lang]['font'][2])
                    label.config(font=new_font)
                    logging.info(
                        f"No.{self.current_sentence} Adjusted {lang} font size from {current_size} to {new_size}")

        self.lang_frame.update_idletasks()

    def _create_language_frame(self, initialize_empty=False):
        self.lang_labels = {}

        self.lang_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.lang_frame.pack(fill=tk.BOTH, expand=True, pady=self.DYNAMIC_LAYOUT['PADDING'])

        language_order = ["한국어", "영어", "중국어"]
        total_height = int(self.screen_height * 0.8)

        height_ratios = {"한국어": 2, "영어": 4, "중국어": 1}
        total_ratio = sum(height_ratios.values())

        label_heights = {lang: int(total_height * ratio / total_ratio) for lang, ratio in height_ratios.items()}
        spacing = int(self.screen_height * 0.01)

        current_y = 0
        for lang in language_order:
            settings = self.LANG_SETTINGS[lang]
            initial_text = "" if initialize_empty else f"샘플 {lang} 텍스트"

            if lang == "영어":
                font = FONT_EN
                initial_font_size = font[1]  # FONT_EN의 두 번째 요소가 크기입니다
            else:
                font_name = settings['font'][0].strip('{}')
                initial_font_size = settings['initial_size']
                font = (font_name, initial_font_size, 'normal')

            wraplength = int(self.screen_width * 0.9) if lang in ["영어", "중국어"] else self.screen_width - 40

            label = tk.Label(self.lang_frame, text=initial_text,
                             font=font, fg=settings['fg'], bg=BG_COLOR,
                             wraplength=wraplength, justify="center")

            label.place(relx=0.5, y=current_y, anchor="n", width=self.screen_width, height=label_heights[lang])

            def create_adjust_font_size(label, initial_size, max_height, font):
                def adjust_font_size():
                    size = initial_size
                    label.config(font=(font[0], size, font[2]))
                    label.update()

                    while label.winfo_reqheight() > max_height and size > 10:
                        size -= 1
                        label.config(font=(font[0], size, font[2]))
                        label.update()

                return adjust_font_size

            label.adjust_font_size = create_adjust_font_size(label, initial_font_size, label_heights[lang], font)
            self.lang_labels[lang] = label

            current_y += label_heights[lang] + spacing

        # 초기 글꼴 크기 조정
        for label in self.lang_labels.values():
            label.adjust_font_size()

    def show_subtitle(self, language):
        displayed_text = self.prepared_subtitles[self.current_sentence][language]
        self.lang_labels[language].config(text=displayed_text)
        self.lang_labels[language].adjust_font_size()
        self.update_idletasks()

    def _create_top_frame(self):
        top_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        top_frame.pack(fill="x", pady=(0, self.DYNAMIC_LAYOUT['PADDING']))

        # 문장 번호를 정중앙에 배치 (노란색)
        self.sentence_label = tk.Label(top_frame, text="",
                                       font=(FONT_NO[0], int(self.DYNAMIC_LAYOUT['TITLE_FONT_SIZE'] * 0.7), FONT_NO[2]),
                                       fg="yellow", bg=BG_COLOR)
        self.sentence_label.place(relx=0.5, rely=0.5, anchor="center")

        # 좌상단에 앱 타이틀 및 배속 정보 표시
        self.title_speed_label = tk.Label(top_frame, text="",
                                          font=(FONT_TOP[0], int(self.DYNAMIC_LAYOUT['TITLE_FONT_SIZE'] * 0.4), FONT_TOP[2]),
                                          fg="white", bg=BG_COLOR, justify="left")
        self.title_speed_label.place(relx=0, rely=0.5, anchor="w", x=20)

        # 우측에 빈 레이블을 추가하여 균형을 맞춤
        spacer_label = tk.Label(top_frame, text="", bg=BG_COLOR, width=len(app_title))
        spacer_label.place(relx=1, rely=0.5, anchor="e", x=-20)

        # top_frame의 높이를 설정
        top_frame.update_idletasks()
        top_frame.config(height=self.sentence_label.winfo_reqheight())

        # 초기 배속 정보 업데이트
        self.update_speed_display()

    def _create_bottom_frame(self):
        bottom_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        bottom_frame.pack(side=tk.BOTTOM, fill="x", pady=(self.DYNAMIC_LAYOUT['PADDING'], 0))

        # 왼쪽 여백을 위한 더미 레이블
        tk.Label(bottom_frame, text="", font=FONT_BOTTOM, fg="white", bg=BG_COLOR, width=10).pack(side=tk.LEFT)

        # "한글속청" 문구를 하단 중앙에 배치 (흰색)
        bottom_label = tk.Label(bottom_frame, text="한글속청 30일 영어 귀가 뚫린다!",
                                font=FONT_BOTTOM, fg="white", bg=BG_COLOR)
        bottom_label.pack(side=tk.LEFT, expand=True)

        # Pause/Resume 버튼을 하단 우측에 배치
        self.pause_button = tk.Button(bottom_frame, text="Pause", command=self.toggle_pause_resume,
                                      font=FONT_START_BUTTON, fg="black", bg="lightgray",
                                      width=5)  # 버튼 너비 지정
        self.pause_button.pack(side=tk.RIGHT, padx=10)

    def _update_sentence_data(self):
        sentence = self.data_manager.get_sentence(self.current_sentence - 1)
        self.sentence_label.config(text=f"No.{self.current_sentence}")

        self.texts["Korean"] = self.split_korean_text(sentence["한국어"])
        self.texts["English"] = self.split_english_text(sentence["영어"])
        self.texts["Chinese"] = sentence["중국어"]

    @staticmethod
    def split_korean_text(text):
        max1 = 23
        if len(text) <= max1:  # 20자 이하면 한 줄로 표시
            return text

        lines = []
        while text:
            if len(text) <= max1:
                lines.append(text)
                break
            split_index = text.rfind(' ', 0, max1)
            if split_index == -1:
                split_index = max1
            lines.append(text[:split_index].strip())
            text = text[split_index:].strip()

        return '\n'.join(lines)

    @staticmethod
    def split_english_text(text):
        max2 = 110
        if len(text) <= max2:  # 100자 이하면 한 줄로 표시
            return text

        lines = []
        while text:
            if len(text) <= max2:
                lines.append(text)
                break
            split_index = text.rfind(' ', 0, max2)
            if split_index == -1:
                split_index = max2
            lines.append(text[:split_index].strip())
            text = text[split_index:].strip()

        return '\n'.join(lines)

    def next_sentence(self):
        if self.current_sentence > self.end:
            self.show_final_message()
            return

        self._update_sentence_data()

        selected_languages = [lang for lang in ["한국어", "영어", "중국어"] if self.audio_vars[lang].get()]

        if selected_languages:
            self.play_audio_and_show_subtitles(selected_languages)
        else:
            self.play_audio_and_show_subtitles([])  # 음성 없이 자막만 표시

    def play_english_audio_and_show_subtitle(self):
        if self.language_vars["영어"].get():
            self.show_subtitle("영어")
        if "영어" in self.audio_languages:
            self.audio_manager.play_sentence_audio(self.current_sentence, "영어", speed=self.audio_speed.get())
        logging.info("Playing English audio and showing English subtitle")

    def prepare_first_subtitle(self):
        first_sentence = self.data_manager.get_sentence(self.current_sentence - 1)
        self.texts["Korean"] = self.split_korean_text(first_sentence["한국어"])
        # 다른 언어의 자막도 필요하다면 여기서 준비합니다.

    def play_audio_and_show_subtitles(self, audio_languages):
        if self.is_paused:
            return
        self.start_time = time.time()
        self.audio_languages = audio_languages
        logging.info(f"No.{self.current_sentence} Playing audio in {audio_languages}")

        # 기본 타이밍 계산
        audio_lengths = {}
        for lang in ["한국어", "영어", "중국어"]:
            if lang in audio_languages:
                speed = self.initial_korean_speed.get() if lang == "한국어" else self.initial_english_speed.get()
                audio_lengths[lang] = int(
                    self.audio_manager.get_audio_length(self.current_sentence, lang) / speed * 1000)
            else:
                audio_lengths[lang] = 0

        # 자막 및 음성 딜레이 설정 적용
        korean_subtitle_delay = int(self.korean_subtitle_delay.get() * 1000)
        english_subtitle_delay = int(self.english_subtitle_delay.get() * 1000)
        english_audio_delay = int(self.english_audio_delay.get() * 1000)
        next_sentence_delay = int(self.next_sentence_delay.get() * 1000)

        # 자막과 음성 사이의 약간의 지연 (예: 200ms)
        subtitle_audio_gap = 200

        # 1. 한국어 처리
        if self.language_vars["한국어"].get():
            self.after(korean_subtitle_delay, lambda: self.show_subtitle("한국어"))
        korean_audio_end = korean_subtitle_delay + subtitle_audio_gap + audio_lengths["한국어"]
        if "한국어" in audio_languages:
            self.after(korean_subtitle_delay + subtitle_audio_gap,
                       lambda: self.audio_manager.play_sentence_audio(self.current_sentence, "한국어",
                                                                      speed=self.korean_audio_speed.get()))

        # 2. 영어 처리
        english_audio_start = korean_audio_end + english_audio_delay
        if self.language_vars["영어"].get():
            self.after(english_subtitle_delay, lambda: self.show_subtitle("영어"))
        if "영어" in audio_languages:
            self.after(english_audio_start,
                       lambda: self.audio_manager.play_sentence_audio(self.current_sentence, "영어",
                                                                      speed=self.english_audio_speed.get()))

        # 3. 중국어 처리
        chinese_audio_start = english_audio_start + audio_lengths["영어"]
        if self.language_vars["중국어"].get():
            if self.show_english_chinese_simultaneously.get():
                # 영어와 동시에 표시
                self.after(english_subtitle_delay, lambda: self.show_subtitle("중국어"))
            else:
                # 영어 자막 1초 후 표시
                self.after(english_subtitle_delay + 1000, lambda: self.show_subtitle("중국어"))
        if "중국어" in audio_languages:
            self.after(chinese_audio_start, self.play_audio("중국어"))

        # 4. 다음 문장으로 넘어가는 시간 계산
        next_sentence_time = chinese_audio_start + audio_lengths["중국어"] + next_sentence_delay

        # 다음 문장으로 넘어가기 직전에 모든 자막 지우기 및 음성 재생 상태 초기화
        self.after(max(0, next_sentence_time - 10), self.clear_all_subtitles_and_reset_audio_state)

        # 다음 문장으로 넘어가기
        self.after(max(0, next_sentence_time), self.proceed_to_next)

        logging.info(f"Next in {next_sentence_time / 1000:.2f} seconds")

    def clear_all_subtitles_and_reset_audio_state(self):
        for language in ["한국어", "영어", "중국어"]:
            self.lang_labels[language].config(text="")
        self.update()
        self.last_adjusted_sentence = 0

        # 음성 재생 상태 초기화 및 디스플레이 업데이트
        self.playing_korean = False
        self.playing_english = False
        self.update_speed_display()

    def play_audio(self, language):
        return lambda: self.audio_manager.play_sentence_audio(
            self.current_sentence,
            language,
            speed=self.audio_speed.get()
        )

    def clear_all_subtitles(self):
        for language in ["한국어", "영어", "중국어"]:
            self.lang_labels[language].config(text="")
        self.update()
        self.last_adjusted_sentence = 0  # 자막을 지울 때 마지막 조정 문장 번호 초기화
        # logging.info("Cleared all subtitles")

    def proceed_to_next(self):
        logging.info(f"No.{self.current_sentence} -> proceeding to next")
        if self.current_sentence >= self.end:
            self.show_final_message()
        elif self.current_sentence % 20 == 0 and self.current_sentence != 0:
            self.show_break_time()
        else:
            self.current_sentence += 1
            self._update_sentence_data()

            # 한국어 자막 즉시 표시 (다른 언어는 원래의 타이밍대로)
            if self.language_vars["한국어"].get():
                self.show_subtitle("한국어")

            self.play_audio_and_show_subtitles(self.audio_languages)

    def show_break_time(self):
        logging.info(f"Break time after No.{self.current_sentence}")
        for widget in self.winfo_children():
            widget.destroy()

        break_frame = tk.Frame(self, bg=self.BG_COLOR)
        break_frame.pack(expand=True, fill="both")

        # Create a center frame to hold all content
        center_frame = tk.Frame(break_frame, bg=self.BG_COLOR)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Break Time and Countdown
        text_countdown_frame = tk.Frame(center_frame, bg=self.BG_COLOR)
        text_countdown_frame.pack(pady=(0, 30))  # Add bottom padding

        break_label = tk.Label(text_countdown_frame, text="Break Time", font=self.FONT_BREAK, fg="white",
                               bg=self.BG_COLOR)
        break_label.pack(side=tk.LEFT, padx=(0, 20))

        countdown_label = tk.Label(text_countdown_frame, text="", font=self.FONT_COUNTDOWN, fg="yellow",
                                   bg=self.BG_COLOR)
        countdown_label.pack(side=tk.LEFT)

        # Message and QR Code
        message_qr_frame = tk.Frame(center_frame, bg=self.BG_COLOR)
        message_qr_frame.pack(pady=(0, 0))

        message_label = tk.Label(message_qr_frame, text="몸에 좋은 소리 mbc 다큐 영상 -->>",
                                 font=("NanumBarunGothic", 40), fg="white", bg=self.BG_COLOR)
        message_label.pack(side=tk.LEFT, padx=(0, 10))

        self.add_qr_code(message_qr_frame)

        self.audio_manager.play_sound("drum")

        drum_duration = self.audio_manager.sounds["drum"].get_length() * 1000
        break_duration = self.GENERAL_SETTINGS['BREAK_TIME']

        def update_countdown(remaining):
            if remaining > 0:
                countdown_label.config(text=f"{remaining}")
                self.after(1000, update_countdown, remaining - 1)
            elif remaining == 0:
                countdown_label.config(text="0")
                self.after(1000, self.resume_after_break)

        self.after(int(drum_duration), update_countdown, break_duration // 1000)

    def resume_after_break(self):
        self.current_sentence += 1
        logging.info(f"Resuming after break, next No.{self.current_sentence}")
        for widget in self.winfo_children():
            widget.destroy()
        self.setup_conversation_screen()
        self.after(100, self.next_sentence)

    def play_final_sound(self):
        self.audio_manager.play_sound("final")

    def finish_application(self):
        self.quit()

    def play_drum_sound_three_times(self):
        for _ in range(2):
            self.audio_manager.play_sound("drum")
            self.after(1500)
        self.after(GENERAL_SETTINGS['FINAL_MESSAGE_DISPLAY_TIME'], self.destroy)

    def save_settings(self):
        try:
            # 입력 필드가 None이 아닌지 확인하고 값을 가져옴
            korean_subtitle_delay = float(
                self.korean_subtitle_entry.get()) if self.korean_subtitle_entry else self.korean_subtitle_delay.get()
            english_subtitle_delay = float(
                self.english_subtitle_entry.get()) if self.english_subtitle_entry else self.english_subtitle_delay.get()
            english_audio_delay = float(
                self.english_audio_entry.get()) if self.english_audio_entry else self.english_audio_delay.get()
            next_sentence_delay = float(
                self.next_sentence_entry.get()) if self.next_sentence_entry else self.next_sentence_delay.get()

            settings = {
                'start_sentence': int(self.start_sentence.get()),
                'end_sentence': int(self.end_sentence.get()),
                'korean_audio_speed': float(self.korean_audio_speed.get()),
                'english_audio_speed': float(self.english_audio_speed.get()),
                # 'audio_speed': float(self.audio_speed.get()),
                'korean_subtitle_delay': korean_subtitle_delay,
                'english_subtitle_delay': english_subtitle_delay,
                'english_audio_delay': english_audio_delay,  # 영어 음성 딜레이 추가
                'next_sentence_delay': next_sentence_delay,
                'show_english_chinese_simultaneously': self.show_english_chinese_simultaneously.get(),
                'initial_korean_speed': float(self.initial_korean_speed.get()),
                'initial_english_speed': float(self.initial_english_speed.get()),
            }

            for lang in ["한국어", "영어", "중국어"]:
                settings[f'show_{lang}'] = self.language_vars[lang].get()
                settings[f'play_{lang}'] = self.audio_vars[lang].get()

            # logging.info(f"Saving settings: {settings}")

            config_dir = CONFIG_FILE.parent
            config_dir.mkdir(parents=True, exist_ok=True)

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)

            # logging.info(f"Settings saved to {CONFIG_FILE}")
        except ValueError as e:
            logging.error(f"Error saving settings: Invalid value - {e}")
            messagebox.showerror("설정 저장 오류", f"잘못된 값이 입력되었습니다: {e}")
        except Exception as e:
            logging.error(f"Error saving settings to {CONFIG_FILE}: {e}")
            messagebox.showerror("설정 저장 오류", f"설정을 저장하는 중 오류가 발생했습니다: {e}")

    def load_settings(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                self.korean_subtitle_delay.set(
                    settings.get('korean_subtitle_delay', self.default_delays['korean_subtitle_delay']))
                self.english_subtitle_delay.set(
                    settings.get('english_subtitle_delay', self.default_delays['english_subtitle_delay']))
                self.english_audio_delay.set(
                    settings.get('english_audio_delay', self.default_delays['english_audio_delay']))  # 영어 음성 딜레이 로드
                self.next_sentence_delay.set(
                    settings.get('next_sentence_delay', self.default_delays['next_sentence_delay']))

                self.start_sentence.set(str(settings.get('start_sentence', "1")))
                self.end_sentence.set(str(settings.get('end_sentence', "100")))
                self.korean_audio_speed.set(settings.get('korean_audio_speed', 2.0))
                self.english_audio_speed.set(settings.get('english_audio_speed', 2.0))
                self.audio_speed.set(settings.get('audio_speed', 2.0))
                self.initial_korean_speed.set(settings.get('initial_korean_speed', 2.0))
                self.initial_english_speed.set(settings.get('initial_english_speed', 2.0))

                for lang in ["한국어", "영어", "중국어"]:
                    self.language_vars[lang].set(settings.get(f'show_{lang}', True))
                    self.audio_vars[lang].set(settings.get(f'play_{lang}', False))

                self.audio_vars["영어"].set(settings.get('play_영어', True))
                self.show_english_chinese_simultaneously.set(settings.get('show_english_chinese_simultaneously', False))

                logging.info("Settings loaded successfully.")
            else:
                logging.info("No settings file found. Using default settings.")
                self._apply_default_settings()
        except json.JSONDecodeError:
            logging.error(f"Error decoding settings file: {CONFIG_FILE}")
            self._apply_default_settings()
        except Exception as e:
            logging.error(f"Error loading settings from {CONFIG_FILE}: {e}")
            self._apply_default_settings()

    def _apply_default_settings(self):
        # 시간 관련 설정 기본값 적용
        self.korean_subtitle_delay.set(self.default_delays['korean_subtitle_delay'])
        self.english_subtitle_delay.set(self.default_delays['english_subtitle_delay'])
        self.english_audio_delay.set(self.default_delays['english_audio_delay'])  # 영어 음성 딜레이 기본값 적용
        self.next_sentence_delay.set(self.default_delays['next_sentence_delay'])

        # 기타 설정 기본값 적용
        self.start_sentence.set("1")
        self.end_sentence.set("100")
        self.initial_korean_speed.set(2.0)
        self.initial_english_speed.set(2.0)
        self.korean_audio_speed.set(2.0)
        self.english_audio_speed.set(2.0)

        # 언어 및 음성 설정 기본값 적용
        for lang in ["한국어", "영어", "중국어"]:
            self.language_vars[lang].set(True)
            self.audio_vars[lang].set(False)

        # 영어 음성은 기본적으로 켜져 있도록 설정
        self.audio_vars["영어"].set(True)

        # 영중 자막 동시 표시 설정 기본값 적용
        self.show_english_chinese_simultaneously.set(False)

        logging.info("Default settings applied.")

    def create_default_settings(self):
        default_settings = {
            'start_sentence': 1,
            'end_sentence': 100,
            'audio_speed': 2.0,
            'korean_subtitle_delay': self.default_delays['korean_subtitle_delay'],
            'english_audio_delay': self.default_delays['english_audio_delay'],
            'english_subtitle_delay': self.default_delays['english_subtitle_delay'],
            'next_sentence_delay': self.default_delays['next_sentence_delay'],
            'show_english_chinese_simultaneously': False,
            'show_한국어': True,
            'show_영어': True,
            'show_중국어': True,
            'play_한국어': False,
            'play_영어': True,
            'play_중국어': False
        }

        try:
            config_dir = CONFIG_FILE.parent
            config_dir.mkdir(parents=True, exist_ok=True)

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, ensure_ascii=False, indent=4)

            logging.info(f"Created default settings file at {CONFIG_FILE}")
            self.load_settings()  # 새로 생성된 설정 파일을 로드
        except Exception as e:
            logging.error(f"Error creating default settings file: {e}")
            self._apply_default_settings()  # 파일 생성에 실패한 경우 메모리에 기본 설정 적용

    def use_default_settings(self):
        # 기본 설정값 적용
        self._apply_default_settings()

        # 기본 설정을 파일로 저장
        default_settings = {
            'start_sentence': int(self.start_sentence.get()),
            'end_sentence': int(self.end_sentence.get()),
            'audio_speed': self.audio_speed.get(),
            'korean_subtitle_delay': self.korean_subtitle_delay.get(),
            'english_audio_delay': self.english_audio_delay.get(),
            'english_subtitle_delay': self.english_subtitle_delay.get(),
            'next_sentence_delay': self.next_sentence_delay.get(),
            'show_english_chinese_simultaneously': self.show_english_chinese_simultaneously.get(),
        }

        for lang in ["한국어", "영어", "중국어"]:
            default_settings[f'show_{lang}'] = self.language_vars[lang].get()
            default_settings[f'play_{lang}'] = self.audio_vars[lang].get()

        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, ensure_ascii=False, indent=4)
            logging.info(f"Default settings saved to {CONFIG_FILE}")
        except Exception as e:
            logging.error(f"Error saving default settings to {CONFIG_FILE}: {e}")

        logging.info("Default settings applied and saved.")

    def on_closing(self):
        self.save_settings()
        self.destroy()


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    logging.info("Application starting")
    app = ConversationApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    logging.info("Entering main loop")
    app.mainloop()
    logging.info("Application closed")
