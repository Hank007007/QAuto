import io
from PIL import Image
import torch
import clip
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 初始化CLIP模型（全局单例）
device = "cuda" if torch.cuda.is_available() else "cpu"

# 从.env读取官方模型名（如ViT-B/32）
model_name = os.getenv("CLIP_MODEL_NAME", "ViT-B/32")

clip_model, clip_preprocess = clip.load(
    model_name,
    device=device,
    jit=False  # 禁用JIT编译，避免兼容性问题
)

for param in clip_model.parameters():
    param.requires_grad = False

def preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    图片预处理（适配CLIP模型）
    :param image_bytes: 图片二进制数据
    :return: 预处理后的PIL图片
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image = image.resize((224, 224), Image.Resampling.LANCZOS)
        return image
    except Exception as e:
        raise RuntimeError(f"图片预处理失败: {str(e)}")

def extract_image_embedding(image_bytes: bytes) -> list:
    """
    提取图片特征向量
    :param image_bytes: 图片二进制数据
    :return: 特征向量列表
    """
    try:
        image = preprocess_image(image_bytes)
        img_tensor = clip_preprocess(image).unsqueeze(0).to(device)
        with torch.no_grad():
            embedding = clip_model.encode_image(img_tensor)
        embedding = embedding / torch.norm(embedding, dim=1, keepdim=True)
        return embedding.cpu().numpy().tolist()[0]
    except Exception as e:
        raise RuntimeError(f"提取图片特征失败: {str(e)}")