# Requirements-to-test traceability

| Requirement | Risks | Implementation | Automated evidence | Manual cases |
| --- | --- | --- | --- | --- |
| US-01 | R03, R10, R11 | Source loading, OBJ and manifest, browser inspector | `test_installed_entry_workflow`, `test_obj_encloses_expected_volume_independently`, browser mesh/picking and fallback | M02, M03, M15, M16, M22 |
| US-02 | R01, R02, R09 | Unit conversion and component comparison | `test_hand_calculated_bottom_masses`, `test_independent_assembly_volume_and_mass`, `test_minimum_thickness_is_supported` | M04–M06 |
| US-03 | R01, R06, R07, R09 | BOM schema, density, totals and revision | `test_faults_fail_for_documented_reason` (stale BOM, wrong units), `test_current_revision_does_not_hide_content_errors` (BOM) | M10, M13 |
| US-04 | R06, R10 | SVG plan metadata, projected geometry and schedule validation | Stale drawing injection and current-revision SVG mutations in `test_artifacts.py` | M11, M23 |
| US-05 | R03, R04, R05, R10 | Inventory checks, bottom support, nonoverlap and copy identity | Missing OBJ stiffener and duplicate ID faults, `test_placement_rejection` | M08, M09, M12, M14 |
| US-06 | R05, R06, R09 | Stable-ID diff, candidate reconciliation and HTML evidence | `test_stiffener_revision_reports_identity_and_position`, `test_compare_can_reconcile_old_exports_against_new_source`, browser revision and report checks | M17, M20, M24 |
| US-07 | R06, R08 | Documented clean install, fixture generator and CLI exits | `test_generate_cli_produces_browser_catalog`, six subprocess fault cases, `test_corrupt_json_has_read_error` | M01, M07 |
| US-08 | R06, R10, R11 | QA dashboard, fault evidence, accessible controls and execution plan | Playwright dashboard, fault navigation, 390 px viewport and WebGL fallback | M18, M19, M21 |

[Requirements](PRODUCT_REQUIREMENTS.md) · [Test strategy](TEST_STRATEGY.md) · [Manual cases](MANUAL_TEST_CASES.md)
