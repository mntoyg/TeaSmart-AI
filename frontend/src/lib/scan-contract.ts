// Generated from design spec section 8. Run npm run generate:contract.
// Empty arrays and objects in the sample deliberately remain unknown.
export type ScanResponse = {
  "scan_id": string;
  "captured_at": string;
  "quality": {
    "passed": boolean;
    "blur_score": number;
    "exposure_mean": number;
    "clipped_low_pct": number;
    "clipped_high_pct": number;
  };
  "prediction": {
    "class_id": number;
    "class_name": string;
    "confidence": number;
    "top_k": {
      "class_name": string;
      "confidence": number;
    }[];
    "low_confidence": boolean;
  };
  "burn_analysis": {
    "verdict": string;
    "burn_likelihood": number;
    "features": {
      "edge_sharpness": number;
      "ring_score": number;
      "acervuli_score": number;
      "edge_affinity": number;
      "colour_zonation": number;
    };
  };
  "severity": {
    "affected_pct": number;
    "level": string;
  };
  "advice": {
    "canonical": string;
    "disease_name_th": string;
    "immediate_action": string;
    "cultural_control": string;
    "chemical_treatment": string;
    "preventive_measures": string;
  };
  "analysis_mode": string;
  "model_version": string;
  "processing_ms": number;
} & { replayed?: boolean };
export const scanShape = {
  "scan_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "captured_at": "2026-10-13T09:12:04+07:00",
  "quality": {
    "passed": true,
    "blur_score": 704.5,
    "exposure_mean": 93.4,
    "clipped_low_pct": 0,
    "clipped_high_pct": 0
  },
  "prediction": {
    "class_id": 0,
    "class_name": "grey_blight",
    "confidence": 0.93,
    "top_k": [
      {
        "class_name": "grey_blight",
        "confidence": 0.93
      },
      {
        "class_name": "brown_blight",
        "confidence": 0.04
      }
    ],
    "low_confidence": false
  },
  "burn_analysis": {
    "verdict": "disease",
    "burn_likelihood": 0.12,
    "features": {
      "edge_sharpness": 0.81,
      "ring_score": 0.74,
      "acervuli_score": 0.66,
      "edge_affinity": 0.19,
      "colour_zonation": 0.71
    }
  },
  "severity": {
    "affected_pct": 0.11,
    "level": "moderate"
  },
  "advice": {
    "canonical": "grey_blight",
    "disease_name_th": "โรคใบไหม้เทา",
    "immediate_action": "...",
    "cultural_control": "...",
    "chemical_treatment": "...",
    "preventive_measures": "..."
  },
  "analysis_mode": "full",
  "model_version": "teasmart-v1",
  "processing_ms": 412
};
export type ClientConfig = {
  "model_version": string;
  "min_confidence": number;
  "class_order": string[];
  "preprocessing": {
    "size": number[];
    "resize": string;
    "preserve_aspect_ratio": boolean;
    "scale": number;
    "mean": number[];
    "std": number[];
    "layout": string;
    "dtype": string;
  };
  "onnx": {
    "file": string;
    "input": string;
    "output": string;
    "output_is_logits": boolean;
  };
  "quality": {
    "blur_threshold": number;
    "exposure_min_mean": number;
    "exposure_max_mean": number;
    "clip_max_pct": number;
  };
  "leaf": {
    "veg_index_min": number;
    "min_fraction": number;
  };
};
export const configShape = {
  "model_version": "teasmart-v1",
  "min_confidence": 0.6,
  "class_order": [
    "grey_blight",
    "brown_blight",
    "algal_spot",
    "healthy",
    "other_disease"
  ],
  "preprocessing": {
    "size": [
      224,
      224
    ],
    "resize": "bilinear",
    "preserve_aspect_ratio": false,
    "scale": 255,
    "mean": [
      0.485,
      0.456,
      0.406
    ],
    "std": [
      0.229,
      0.224,
      0.225
    ],
    "layout": "NCHW",
    "dtype": "float32"
  },
  "onnx": {
    "file": "teasmart-v1.onnx",
    "input": "input",
    "output": "logits",
    "output_is_logits": true
  },
  "quality": {
    "blur_threshold": 15,
    "exposure_min_mean": 40,
    "exposure_max_mean": 235,
    "clip_max_pct": 0.1
  },
  "leaf": {
    "veg_index_min": 0.05,
    "min_fraction": 0.002
  }
};
export const transportLimits = {
  "max_upload_bytes": 8388608,
  "max_image_pixels": 40000000,
  "max_batch_items": 20,
  "max_batch_bytes": 33554432
};
