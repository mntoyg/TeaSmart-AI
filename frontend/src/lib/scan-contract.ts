// Generated from design spec section 8. Run npm run generate:contract.
// Empty arrays and objects in the sample deliberately remain unknown.
export type ScanResponse = {
  "scan_id": string;
  "quality": {
    "passed": boolean;
    "blur_score": number;
    "exposure_score": number;
  };
  "prediction": {
    "class_id": number;
    "class_name": string;
    "confidence": number;
    "top_k": unknown[];
  };
  "burn_analysis": {
    "verdict": string;
    "burn_likelihood": number;
    "features": Record<string, unknown>;
  };
  "severity": {
    "affected_pct": number;
    "level": string;
  };
  "advice": {
    "disease_name_th": string;
    "immediate_action": string;
  };
  "model_version": string;
  "processing_ms": number;
};
