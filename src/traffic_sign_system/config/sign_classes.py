"""
Sign class labels (GTSRB 43 classes) and hazard prediction rules.
"""

# -- Class Labels --------------------------------------------------------------
SIGN_LABELS = {
    0:  "Speed limit (20km/h)",
    1:  "Speed limit (30km/h)",
    2:  "Speed limit (50km/h)",
    3:  "Speed limit (60km/h)",
    4:  "Speed limit (70km/h)",
    5:  "Speed limit (80km/h)",
    6:  "End of speed limit (80km/h)",
    7:  "Speed limit (100km/h)",
    8:  "Speed limit (120km/h)",
    9:  "No passing",
    10: "No passing for vehicles over 3.5t",
    11: "Right-of-way at intersection",
    12: "Priority road",
    13: "Yield",
    14: "Stop",
    15: "No vehicles",
    16: "Vehicles over 3.5t prohibited",
    17: "No entry",
    18: "General caution",
    19: "Dangerous curve left",
    20: "Dangerous curve right",
    21: "Double curve",
    22: "Bumpy road",
    23: "Slippery road",
    24: "Road narrows on right",
    25: "Road work",
    26: "Traffic signals",
    27: "Pedestrians",
    28: "Children crossing",
    29: "Bicycles crossing",
    30: "Beware of ice/snow",
    31: "Wild animals crossing",
    32: "End of all speed & passing limits",
    33: "Turn right ahead",
    34: "Turn left ahead",
    35: "Ahead only",
    36: "Go straight or right",
    37: "Go straight or left",
    38: "Keep right",
    39: "Keep left",
    40: "Roundabout mandatory",
    41: "End of no passing",
    42: "End of no passing (3.5t)",
}

# -- Hazard Prediction Rules ---------------------------------------------------
# Format: class_id -> {level, message, action, color_hex}
HAZARD_RULES = {
    # Speed limits
    0:  {"level": "info",    "message": "Speed limit: 20 km/h",  "action": "Reduce speed immediately",    "color": "#3B8BD4"},
    1:  {"level": "info",    "message": "Speed limit: 30 km/h",  "action": "Keep speed below 30 km/h",   "color": "#3B8BD4"},
    2:  {"level": "info",    "message": "Speed limit: 50 km/h",  "action": "Keep speed below 50 km/h",   "color": "#3B8BD4"},
    3:  {"level": "info",    "message": "Speed limit: 60 km/h",  "action": "Keep speed below 60 km/h",   "color": "#3B8BD4"},
    4:  {"level": "info",    "message": "Speed limit: 70 km/h",  "action": "Keep speed below 70 km/h",   "color": "#3B8BD4"},
    5:  {"level": "info",    "message": "Speed limit: 80 km/h",  "action": "Keep speed below 80 km/h",   "color": "#3B8BD4"},
    6:  {"level": "info",    "message": "End of speed limit 80",  "action": "Speed limit ended",           "color": "#3B8BD4"},
    7:  {"level": "info",    "message": "Speed limit: 100 km/h", "action": "Keep speed below 100 km/h",  "color": "#3B8BD4"},
    8:  {"level": "info",    "message": "Speed limit: 120 km/h", "action": "Keep speed below 120 km/h",  "color": "#3B8BD4"},
    # Mandatory stops
    14: {"level": "critical","message": "STOP sign detected",    "action": "Come to a complete stop",     "color": "#E24B4A"},
    17: {"level": "critical","message": "No entry ahead",        "action": "Do not proceed - wrong way", "color": "#E24B4A"},
    # Yield & priority
    13: {"level": "warning", "message": "Yield ahead",           "action": "Slow down and give way",     "color": "#EF9F27"},
    11: {"level": "warning", "message": "Right-of-way ahead",    "action": "Proceed with caution",       "color": "#EF9F27"},
    12: {"level": "info",    "message": "Priority road",         "action": "You have right of way",      "color": "#3B8BD4"},
    # Hazard warnings
    18: {"level": "warning", "message": "General caution",       "action": "Stay alert - hazard ahead",  "color": "#EF9F27"},
    19: {"level": "warning", "message": "Dangerous curve left",  "action": "Reduce speed before curve",  "color": "#EF9F27"},
    20: {"level": "warning", "message": "Dangerous curve right", "action": "Reduce speed before curve",  "color": "#EF9F27"},
    21: {"level": "warning", "message": "Double curve",          "action": "Reduce speed - curves ahead","color": "#EF9F27"},
    22: {"level": "warning", "message": "Bumpy road ahead",      "action": "Slow down - uneven surface", "color": "#EF9F27"},
    23: {"level": "warning", "message": "Slippery road",         "action": "Slow down - risk of skid",   "color": "#EF9F27"},
    24: {"level": "warning", "message": "Road narrows right",    "action": "Adjust course carefully",    "color": "#EF9F27"},
    25: {"level": "warning", "message": "Road works ahead",      "action": "Slow down - workers present","color": "#EF9F27"},
    26: {"level": "warning", "message": "Traffic signals ahead", "action": "Prepare to stop",            "color": "#EF9F27"},
    27: {"level": "warning", "message": "Pedestrian zone",       "action": "Watch for pedestrians",      "color": "#EF9F27"},
    28: {"level": "warning", "message": "Children crossing",     "action": "Stop if children present",   "color": "#EF9F27"},
    29: {"level": "warning", "message": "Bicycles crossing",     "action": "Watch for cyclists",         "color": "#EF9F27"},
    30: {"level": "warning", "message": "Ice/snow possible",     "action": "Engage winter driving mode", "color": "#EF9F27"},
    31: {"level": "warning", "message": "Wild animals crossing", "action": "Watch for animals on road",  "color": "#EF9F27"},
    32: {"level": "info",    "message": "End of limits",         "action": "All restrictions removed",   "color": "#3B8BD4"},
    # No-passing zones
    9:  {"level": "info",    "message": "No passing zone",       "action": "Stay in lane",               "color": "#3B8BD4"},
    10: {"level": "info",    "message": "No passing (HGV)",      "action": "Heavy vehicles: stay in lane","color": "#3B8BD4"},
    # Mandatory directions
    33: {"level": "info",    "message": "Turn right ahead",      "action": "Prepare to turn right",      "color": "#1D9E75"},
    34: {"level": "info",    "message": "Turn left ahead",       "action": "Prepare to turn left",       "color": "#1D9E75"},
    35: {"level": "info",    "message": "Ahead only",            "action": "Keep straight",              "color": "#1D9E75"},
    36: {"level": "info",    "message": "Go straight or right",  "action": "Proceed straight or right",  "color": "#1D9E75"},
    37: {"level": "info",    "message": "Go straight or left",   "action": "Proceed straight or left",   "color": "#1D9E75"},
    38: {"level": "info",    "message": "Keep right",            "action": "Move to the right lane",     "color": "#1D9E75"},
    39: {"level": "info",    "message": "Keep left",             "action": "Move to the left lane",      "color": "#1D9E75"},
    40: {"level": "info",    "message": "Roundabout ahead",      "action": "Slow down and yield",        "color": "#1D9E75"},
    41: {"level": "info",    "message": "End of no passing",     "action": "Passing restrictions lifted","color": "#3B8BD4"},
    42: {"level": "info",    "message": "End of no passing (HGV)","action": "HGV restrictions lifted",   "color": "#3B8BD4"},
}

HAZARD_LEVEL_PRIORITY = {"critical": 3, "warning": 2, "info": 1}

def get_hazard(class_id: int) -> dict:
    """Return hazard info for a given sign class, with fallback."""
    label = SIGN_LABELS.get(class_id, f"Unknown sign ({class_id})")
    default = {
        "level":   "info",
        "message": label,
        "action":  "Observe sign and comply",
        "color":   "#888780",
    }
    rule = HAZARD_RULES.get(class_id, default)
    rule["label"] = label
    rule["class_id"] = class_id
    return rule
