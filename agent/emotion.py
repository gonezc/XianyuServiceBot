"""
情绪分析模块

优先加载显式本地 Transformer 情感模型；如果本地模型缺失或损坏，
则降级为完全离线的词典情绪引擎，不会连接 Hugging Face。
"""
import logging
import math
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Dict, Iterable, Optional

from loguru import logger

# 抑制 TensorFlow / protobuf 警告
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)


class _SuppressProtobufErrors:
    def __init__(self, stream):
        self._stream = stream

    def write(self, msg):
        if "MessageFactory" not in msg and "GetPrototype" not in msg:
            self._stream.write(msg)

    def flush(self):
        self._stream.flush()


sys.stderr = _SuppressProtobufErrors(sys.stderr)

try:
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        pipeline,
    )

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers 未安装，将使用离线词典情绪引擎")


def _env_flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


EMOTION_MODEL_NAME = os.getenv(
    "EMOTION_MODEL_NAME",
    "uer/roberta-base-finetuned-jd-binary-chinese",
)
USE_EMOTION_MODEL = _env_flag("USE_EMOTION_MODEL", True)
NEUTRAL_THRESHOLD = float(os.getenv("EMOTION_NEUTRAL_THRESHOLD", "0.83"))
MODEL_CACHE_DIR = Path(os.getenv("HUGGINGFACE_CACHE_DIR", r"D:\develop\huggingface"))
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 优先使用显式本地目录；允许未来直接投放一个完整的本地模型目录。
ENV_MODEL_PATH = os.getenv("EMOTION_MODEL_PATH", "").strip()
DEFAULT_LOCAL_MODEL_DIR = PROJECT_ROOT / "data" / "models" / "emotion"
HF_CACHE_MODEL_DIR = (
    MODEL_CACHE_DIR
    / "hub"
    / "models--uer--roberta-base-finetuned-jd-binary-chinese"
)

POSITIVE_PHRASES = {
    "没问题": 2.2,
    "可以的": 1.8,
    "可以": 1.3,
    "行的": 1.8,
    "行": 1.2,
    "好嘞": 2.0,
    "好的": 1.6,
    "好": 0.8,
    "不错": 1.5,
    "满意": 2.3,
    "靠谱": 2.0,
    "专业": 1.6,
    "感谢": 1.6,
    "谢谢": 1.8,
    "辛苦": 1.2,
    "合作": 1.4,
    "下单": 2.4,
    "拍了": 2.4,
    "付款": 2.6,
    "成交": 2.8,
    "就你": 1.5,
    "安排": 1.2,
    "尽快": 0.8,
    "期待": 1.4,
    "赞": 1.8,
}

NEGATIVE_PHRASES = {
    "太贵": 2.2,
    "贵了": 1.9,
    "有点贵": 1.6,
    "贵": 1.0,
    "便宜点": 1.1,
    "优惠点": 1.2,
    "再少点": 1.2,
    "预算不够": 1.8,
    "不行": 1.8,
    "不太行": 2.1,
    "不满意": 2.6,
    "不好": 1.8,
    "不靠谱": 2.7,
    "不专业": 2.4,
    "算了": 2.8,
    "不用了": 2.8,
    "不考虑": 2.6,
    "先不了": 2.2,
    "再看看": 1.0,
    "生气": 3.0,
    "失望": 2.8,
    "垃圾": 3.5,
    "骗子": 3.8,
    "投诉": 3.2,
    "太慢": 2.0,
    "真慢": 2.0,
    "离谱": 2.6,
    "扯": 2.0,
    "不回": 1.5,
}

NEGATIONS = ("不", "没", "无", "别", "非")
INTENSIFIERS = {
    "很": 0.15,
    "真": 0.2,
    "太": 0.35,
    "非常": 0.4,
    "特别": 0.35,
    "超级": 0.45,
    "有点": 0.1,
    "稍微": 0.1,
}


def _looks_zero_filled(file_path: Path, sample_size: int = 4096) -> bool:
    try:
        if not file_path.exists() or file_path.stat().st_size == 0:
            return True
        with file_path.open("rb") as f:
            chunk = f.read(sample_size)
        return bool(chunk) and all(byte == 0 for byte in chunk)
    except OSError:
        return True


def _is_valid_local_model_dir(model_dir: Path) -> bool:
    required_files = [
        model_dir / "config.json",
        model_dir / "pytorch_model.bin",
        model_dir / "vocab.txt",
    ]
    return all(not _looks_zero_filled(path) for path in required_files)


def _iter_model_candidates() -> Iterable[Path]:
    if ENV_MODEL_PATH:
        yield Path(ENV_MODEL_PATH)

    if DEFAULT_LOCAL_MODEL_DIR.exists():
        for child in DEFAULT_LOCAL_MODEL_DIR.iterdir():
            if child.is_dir():
                yield child
        yield DEFAULT_LOCAL_MODEL_DIR

    if HF_CACHE_MODEL_DIR.exists():
        snapshots_dir = HF_CACHE_MODEL_DIR / "snapshots"
        if snapshots_dir.exists():
            for child in snapshots_dir.iterdir():
                if child.is_dir():
                    yield child


def _resolve_local_model_dir() -> Optional[Path]:
    for candidate in _iter_model_candidates():
        if _is_valid_local_model_dir(candidate):
            return candidate
        logger.warning(f"跳过损坏或不完整的情感模型目录: {candidate}")
    return None


class EmotionAnalyzer:
    """情绪分析器。

    1. 优先从本地目录加载 Transformers 模型
    2. 加载失败时退回离线词典引擎
    """

    def __init__(self, use_model: bool = None):
        self.use_model = use_model if use_model is not None else USE_EMOTION_MODEL
        self.analyzer = None
        self.backend = "local_lexicon"

        if self.use_model and TRANSFORMERS_AVAILABLE:
            local_model_dir = _resolve_local_model_dir()
            if local_model_dir is None:
                logger.warning(
                    "未找到可用的本地情感模型目录，使用离线词典情绪引擎"
                )
            else:
                try:
                    logger.info(f"加载本地情感模型: {local_model_dir}")
                    tokenizer = AutoTokenizer.from_pretrained(
                        str(local_model_dir),
                        local_files_only=True,
                        use_fast=False,
                    )
                    model = AutoModelForSequenceClassification.from_pretrained(
                        str(local_model_dir),
                        local_files_only=True,
                    )
                    self.analyzer = pipeline(
                        "sentiment-analysis",
                        model=model,
                        tokenizer=tokenizer,
                        device=-1,
                    )
                    self.backend = "local_transformers"
                    logger.info("本地情感模型加载成功")
                except Exception as e:
                    logger.error(f"本地情感模型加载失败: {e}，改用离线词典引擎")
                    self.analyzer = None
                    self.use_model = False

    def analyze(self, text: str, context: str = "") -> Dict[str, any]:
        """分析情绪。"""
        full_text = f"{context}\n{text}" if context else text

        if self.analyzer:
            try:
                result = self.analyzer(full_text)
                if result:
                    label = str(result[0].get("label", "")).lower()
                    score = float(result[0].get("score", 0.5))

                    if score < NEUTRAL_THRESHOLD:
                        sentiment = "neutral"
                    elif "positive" in label or label == "label_1":
                        sentiment = "positive"
                    elif "negative" in label or label == "label_0":
                        sentiment = "negative"
                    else:
                        sentiment = "neutral"

                    return {
                        "sentiment": sentiment,
                        "confidence": score,
                        "method": self.backend,
                    }
            except Exception as e:
                logger.warning(f"本地情感模型推理失败: {e}，降级为离线词典引擎")

        return self._analyze_by_lexicon(full_text)

    def _analyze_by_lexicon(self, text: str) -> Dict[str, any]:
        normalized = text.lower().strip()
        if not normalized:
            return {
                "sentiment": "neutral",
                "confidence": 0.55,
                "method": "local_lexicon",
            }

        segments = [seg for seg in re.split(r"[\s,，。！？!?\n\r；;]+", normalized) if seg]
        total_score = 0.0

        # 先做整句短语匹配，命中业务场景常见表达。
        total_score += self._collect_phrase_score(normalized)

        # 再做分段补充，处理“谢谢，先拍了”“有点贵，能便宜点吗”这种组合表达。
        for seg in segments:
            total_score += self._collect_phrase_score(seg) * 0.35

        total_score += self._punctuation_bias(normalized)

        magnitude = abs(total_score)
        if magnitude < 0.9:
            sentiment = "neutral"
        elif total_score > 0:
            sentiment = "positive"
        else:
            sentiment = "negative"

        confidence = self._confidence_from_score(magnitude, sentiment, normalized)
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "method": "local_lexicon",
        }

    def _collect_phrase_score(self, text: str) -> float:
        score = 0.0

        for phrase, weight in POSITIVE_PHRASES.items():
            score += self._phrase_score(text, phrase, weight, positive=True)

        for phrase, weight in NEGATIVE_PHRASES.items():
            score += self._phrase_score(text, phrase, weight, positive=False)

        return score

    def _phrase_score(self, text: str, phrase: str, weight: float, positive: bool) -> float:
        total = 0.0
        start = 0
        while True:
            idx = text.find(phrase, start)
            if idx < 0:
                break

            window = text[max(0, idx - 3) : idx]
            adjusted = weight * (1 + self._intensifier_bonus(window))
            sign = 1.0 if positive else -1.0

            if self._has_negation(window):
                sign *= -1.0
                adjusted *= 0.9

            total += adjusted * sign
            start = idx + len(phrase)
        return total

    def _has_negation(self, prefix: str) -> bool:
        return any(prefix.endswith(token) for token in NEGATIONS)

    def _intensifier_bonus(self, prefix: str) -> float:
        bonus = 0.0
        for word, delta in INTENSIFIERS.items():
            if prefix.endswith(word):
                bonus = max(bonus, delta)
        return bonus

    def _punctuation_bias(self, text: str) -> float:
        bias = 0.0
        if "??" in text or "？？" in text:
            bias -= 0.4
        if "!!!" in text or "！！！" in text:
            bias -= 0.6
        if text.endswith("~"):
            bias += 0.15
        if "?" in text or "？" in text:
            bias -= 0.05
        return bias

    def _confidence_from_score(self, magnitude: float, sentiment: str, text: str) -> float:
        if sentiment == "neutral":
            base = 0.56 + min(magnitude, 0.8) * 0.08
            if "?" in text or "？" in text:
                base += 0.02
            return round(min(base, 0.68), 3)

        base = 0.64 + 0.22 * math.tanh(magnitude / 2.4)
        if sentiment == "negative" and any(word in text for word in ("投诉", "骗子", "垃圾")):
            base += 0.06
        if sentiment == "positive" and any(word in text for word in ("付款", "下单", "成交")):
            base += 0.05
        return round(min(base, 0.95), 3)


_emotion_analyzer: Optional[EmotionAnalyzer] = None


def get_emotion_analyzer() -> EmotionAnalyzer:
    """获取情绪分析器实例（单例）。"""
    global _emotion_analyzer
    if _emotion_analyzer is None:
        _emotion_analyzer = EmotionAnalyzer()
    return _emotion_analyzer
