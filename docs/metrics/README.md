# 📊 Code Metrics
Generated on: Sat Jun 28 13:44:34 UTC 2025

## 📈 Test Coverage
======================== 8 passed, 3 warnings in 1.52s =========================

## 🔍 Code Complexity
main.py
    F 71:0 _auto_include_routers - A
    F 23:0 lifespan - A
    F 46:0 create_app - A
    F 104:0 root - A
    F 110:0 health_check - A
tests/modules/webhook_receiver/test_webhook_receiver.py
    F 82:0 test_webhook_endpoint_valid_signature - B
    F 215:0 test_root_endpoint - A
    F 108:0 test_webhook_endpoint_invalid_signature - A
    F 124:0 test_webhook_endpoint_missing_signature - A
    F 139:0 test_webhook_endpoint_unsupported_event - A
    F 170:0 test_webhook_multiple_commits - A
    F 208:0 test_health_check - A
    F 155:0 test_webhook_endpoint_malformed_json - A
    F 18:0 _create_signature - A
    F 25:0 setup_local_settings - A
    F 38:0 _sample_github_payload - A
infrastructure/aws/s3_client.py
    C 21:0 S3Client - A
    M 24:4 S3Client.__init__ - A
    M 39:4 S3Client.upload_diff - A
    M 60:4 S3Client.get_presigned_url - A
shared/config/database.py
    F 21:0 get_engine - A
    F 41:0 get_session_maker - A
    F 58:0 get_session - A
    F 74:0 get_async_session - A
    F 88:0 create_tables - A
    F 31:0 get_sync_engine - A
    F 51:0 get_sync_session_maker - A
    F 99:0 create_tables_sync - A
    C 15:0 Base - A
shared/config/settings.py
    F 85:0 get_settings - A
    C 10:0 Settings - A
shared/config/celery_app.py
    F 33:0 create_celery_app - A
    C 17:0 MockCelery - A
    M 20:4 MockCelery.send_task - A
shared/utils/logging.py
    F 206:0 simplify_data - D
    M 139:4 ModuleIOLogger._summarize_data - C
    F 191:0 default_json_serializer - B
    C 67:0 ModuleIOLogger - B
    M 95:4 ModuleIOLogger.log_output - A
    F 288:0 log_module_io - A
    F 335:0 log_processing_chain_end - A
    M 118:4 ModuleIOLogger.log_error - A
    M 77:4 ModuleIOLogger.log_input - A
    F 32:0 setup_detailed_logging - A
    F 313:0 log_processing_chain_start - A
    M 70:4 ModuleIOLogger.__init__ - A
scripts/migrate_database.py
    F 19:0 main - B

47 blocks (classes, functions, methods) analyzed.
Average complexity: A (3.3191489361702127)
