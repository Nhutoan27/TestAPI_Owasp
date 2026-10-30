from app.reports.benchmark import GroundTruthItem, ReportedFinding, evaluate_against_ground_truth


def test_evaluate_against_ground_truth_computes_rates_with_mix_of_outcomes() -> None:
    ground_truth = [
        GroundTruthItem("/users/{username}", "API1:2023"),
        GroundTruthItem("/users/{username}/email", "API3:2023"),
        GroundTruthItem("/admin/users", "API5:2023"),
    ]
    # Phat hien dung 2/3 (thieu 1 - false negative), them 1 bao sai (false positive).
    findings = [
        ReportedFinding("/users/{username}", "API1:2023"),
        ReportedFinding("/admin/users", "API5:2023"),
        ReportedFinding("/books/{id}", "API1:2023"),
    ]

    result = evaluate_against_ground_truth(findings, ground_truth)

    assert result.true_positives == 2
    assert result.false_negatives == 1
    assert result.false_positives == 1
    assert result.detection_rate == 2 / 3
    assert result.false_positive_rate == 1 / 3


def test_evaluate_against_ground_truth_perfect_detection_no_false_positives() -> None:
    ground_truth = [GroundTruthItem("/x", "API1:2023")]
    findings = [ReportedFinding("/x", "API1:2023")]

    result = evaluate_against_ground_truth(findings, ground_truth)

    assert result.detection_rate == 1.0
    assert result.false_positive_rate == 0.0


def test_evaluate_against_ground_truth_empty_inputs_do_not_divide_by_zero() -> None:
    result = evaluate_against_ground_truth([], [])

    assert result.detection_rate == 0.0
    assert result.false_positive_rate == 0.0
