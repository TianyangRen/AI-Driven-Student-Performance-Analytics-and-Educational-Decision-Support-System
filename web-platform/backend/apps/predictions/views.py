"""
Predictions API。

本文件【不直接】调用任何 ML 库 —— 全部模型相关调用都走 services.predict_risk()
适配层，从而：
  - 当组员 ml/ 模块未集成时：services 自动返回 mock，本视图无需感知
  - 当组员 ml/ 模块接入后：services 自动启用真实推理，本视图同样无需改动
"""
import random
from datetime import datetime, timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from common.responses import ok

from .services import build_features_for_student, predict_risk, ml_status


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_prediction(request, section_id):
    """
    触发一次 section 级预测运行。

    真实接入后流程：
      1) 创建 PredictionRun 行（status=RUNNING）
      2) 遍历 section 内学生 → build_features_for_student → predict_risk
      3) 批量写入 RiskPrediction 表
      4) 更新 PredictionRun.status=SUCCESS
    当前实现仅返回 mock run_id，结构与上面流程兼容。
    """
    status_meta = ml_status()
    return ok({
        "run_id": random.randint(1000, 9999),
        "section_id": section_id,
        "status": "SUCCESS",
        "model_version": status_meta.get("risk_classifier", {}).get("version", "mock-fallback"),
        "feature_cutoff_date": request.data.get("feature_cutoff_date"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ml_mode": status_meta.get("mode", "mock"),
    }, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_predictions(request, section_id):
    """
    返回 section 内学生的最近一次预测列表。
    真实接入后从 RiskPrediction 表按 section + 最新 run_id 查询。
    """
    random.seed(section_id or 1)
    items = []
    for i in range(1, 21):
        # 这一段在真实接入后改为：
        #   features = build_features_for_student(student, section)
        #   r = predict_risk(features)
        r = predict_risk({})
        items.append({
            "prediction_id": 90000 + i,
            "student_id": i,
            "anonymized_code": f"S-ANON-{i:03d}",
            "probability": r["probability"],
            "risk_level": r["risk_level"],
        })
    return ok(items)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def explanation(request, prediction_id):
    """
    单条预测的 SHAP / 特征贡献解释。
    真实接入后：根据 prediction_id 反查学生 + 模型版本 → 再次调用 explain。
    当前实现：直接调 predict_risk() 获取 top_factors，结构一致。
    """
    r = predict_risk({})  # 真接入后传 build_features_for_student(...)
    return ok({
        "prediction_id": prediction_id,
        "student_code": f"S-ANON-{prediction_id % 100:03d}",
        "probability": r["probability"],
        "risk_level": r["risk_level"],
        "model_version": r["model_version"],
        "top_factors": r["top_factors"],
        "suggestion": "建议教师优先核验近期作业完成情况，并安排一次针对性沟通。",
        "disclaimer": "该结果仅为教学辅助信号，不构成自动化学术结论。",
    })
