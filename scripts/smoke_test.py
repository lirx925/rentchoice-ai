"""Run core offline checks without launching Streamlit."""
from pathlib import Path
import sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import src.storage as storage
from src.data_loader import load_listings, REQUIRED_COLUMNS
from src.experiment import GROUPS, assign_treatment, build_choice_sets, welfare_metrics
from src.explanations import rule_based_explanation
from src.recommender import score_listings

PREFS={"budget_max":7000,"ideal_rent":5500,"destination_district":"浦东","min_area":35,"rental_type_preference":"no_shared","metro_priority":True,"importance_rent":5,"importance_location":5,"importance_area":4,"importance_metro":4}

def main():
    listings=load_listings(); assert len(listings)>=36 and REQUIRED_COLUMNS<=set(listings)
    scored=score_listings(listings,PREFS); assert scored.recommendation_score.between(0,100).all()
    sets=build_choice_sets(listings,"test-participant"); assert len(sets)==6 and all(len(x)==len(set(x))==3 for x in sets)
    assert assign_treatment("test-participant") in GROUPS
    opts=scored[scored.listing_id.isin(sets[0])]; best=opts.loc[opts.recommendation_score.idxmax()]
    chosen,best_u,loss=welfare_metrics(opts,str(opts.iloc[0].listing_id)); assert loss>=0 and best_u>=chosen
    explanation=rule_based_explanation(best,opts[opts.listing_id!=best.listing_id],PREFS); assert "优点" in explanation and "不足" in explanation
    assert set(scored["location_fit"].unique()).issubset({40.0, 100.0})
    same = listings.iloc[0].copy(); same["district"] = "浦东"
    other = listings.iloc[0].copy(); other["district"] = "徐汇"
    same_score = score_listings(pd.DataFrame([same]), PREFS).iloc[0]["location_fit"]
    other_score = score_listings(pd.DataFrame([other]), PREFS).iloc[0]["location_fit"]
    assert same_score == 100 and other_score == 40
    with tempfile.TemporaryDirectory() as tmp:
        old_files=storage.FILES; storage.DATA_DIR=Path(tmp); storage.FILES={k:Path(tmp)/f"{k}.csv" for k in old_files}
        storage.save_choice({"participant_id":"p","round_number":1,"chosen_listing_id":"R001"}); storage.save_choice({"participant_id":"p","round_number":1,"chosen_listing_id":"R002"})
        assert len(storage.load_all_results()["choices"])==1
        storage.save_participant({"participant_id":"p","treatment_group":"control","consent":True})
        progress = storage.load_participant_progress("p")
        assert progress and progress["choices"][0]["chosen_listing_id"] == "R002"
        assert storage.load_participant_progress("missing") is None
        # Old append-only datasets can have duplicate and malformed rounds.
        pd.DataFrame([
            {"participant_id":"p","round_number":2,"chosen_listing_id":"R003","created_at":"2026-01-01"},
            {"participant_id":"p","round_number":2,"chosen_listing_id":"R004","created_at":"2026-01-02"},
            {"participant_id":"p","round_number":"bad","chosen_listing_id":"R005","created_at":"2026-01-03"},
        ]).to_csv(storage.FILES["choices"], index=False)
        progress = storage.load_participant_progress("p")
        assert len(progress["choices"]) == 1 and progress["choices"][0]["chosen_listing_id"] == "R004"
        storage.FILES=old_files
    print("PASS: listings, scores, choice sets, groups, welfare, explanation, local idempotent storage")

if __name__=="__main__": main()
