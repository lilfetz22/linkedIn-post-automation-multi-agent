# CHANGELOG

<!-- version list -->

## v1.5.0 (2025-12-20)

### Documentation

- **github**: Update first-time setup wording to accept any custom field
  ([`fd8c220`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/fd8c2201dcb0aa5b8db67a706561f13b5d5a52a0))

- **readme**: Clarify field selection and examples for freeform fields
  ([`6c9ca8c`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/6c9ca8c24a5d2f0392b430e536a18dfc84df3e88))

### Features

- **config**: Allow arbitrary custom field input in CLI and config
  ([`4ae2c19`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/4ae2c192ba5b00ccd326850d301c6b22894b3203))


## v1.4.0 (2025-12-14)

### Bug Fixes

- **agents/image-generator**: Simplify print statements in standalone test output
  ([`e276882`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/e276882b6d789e05a005d70e1e2a38804d3e0306))

- **core/llm-clients**: Use correct response_modalities value for image generation
  ([`0e495b0`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/0e495b04cb430800e911afdaba6b45a717470ed5))

- **core/llm_clients**: Format note for clarity in image generation response modalities
  ([`d5d1f4c`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/d5d1f4c465925138530950ac650393ee868c8bb4))

- **cost_tracking**: Accept keyword args in record_call for backwards-compatible API
  ([`b628570`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/b628570e86f6f10e10709ce6b6b7b28074dda654))

- **cost_tracking**: Make agent_name_or_model optional to support pure keyword calls
  ([`9f9a1c1`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/9f9a1c158643771873efab0a41b0d5b34b821c58))

- **orchestrator**: Record agent failure metrics when circuit breaker trips\n\nAdd explicit except
  CircuitBreakerTrippedError in _execute_agent_with_retry() to log duration and error details before
  propagating. This ensures un_failed.json and metrics capture the failed step even if the breaker
  opens mid-execution.
  ([`a131de0`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/a131de0c271b457086e61b2b0b992bafdffbabdb))

- **retry**: Treat Gemini quota/rate-limit errors as non-retryable to avoid futile retries and
  circuit breaker trips\n\nAdd _is_quota_or_rate_limit_error() to detect RESOURCE_EXHAUSTED/quota
  exceeded/rate limit messages. When detected, flip etryable to false and surface actionable
  guidance. This prevents exponential backoff from hammering the API and stops breaker from
  accumulating failures on quota issues.\n\nImpact:\n- More graceful aborts under quota
  exhaustion\n- Clearer error messaging for remediation\n- Preserves circuit breaker for genuine
  transient failures
  ([`1055678`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/105567827c62baea2145b51a3fbc76b99b7897da))

- **reviewer**: Scrub forbidden newsletter mentions and improve review pipeline
  ([`c42e5eb`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/c42e5eb80dd6f1025a9ca86e8d5aaa2b8c57feee))

- **reviewer**: Use positional args when recording cost and include agent name
  ([`a30c6fa`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/a30c6fad77e31b761bc7bed43860f882792ca651))

- **writer**: Remove newsletter sign-off and scrub forbidden mentions
  ([`c7efe0d`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/c7efe0d794e97653f7de1fe207d8b92631878a93))

- **writer_agent**: Accept structured_prompt string and use it as LLM prompt
  ([`f827069`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/f82706969d68647d07073088b331bd53fc040213))

### Features

- **agents/image-generator**: Capture full tracebacks on ModelError and add standalone CLI for
  testing
  ([`b608511`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/b608511ed9415cb9867d3e789fc654fa2fbcbc42))


## v1.3.0 (2025-12-13)


## v1.2.0 (2025-12-13)

### Bug Fixes

- Resolve flake8 line length issue in main.py
  ([`1224284`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/12242849cd2df1e99b76a5c6f16b9ca0d4d7c908))

- **orchestrator**: Omit image artifact in run summary when --no-image is set
  ([`2717d07`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/2717d07fd0bd53ff7ac9b7836177d60f55f0a187))

### Documentation

- Add --no-image flag documentation and cost optimization section
  ([`cdab745`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/cdab745fdd85f05ed8d03f83937693fc8fc7a157))

- **readme**: Update README.md to clarify command line execution and mark phases 11 and 12 as
  complete
  ([`9f069b5`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/9f069b55b5662ea1a97bd9506208648c0494d718))

### Features

- Add --no-image CLI flag to skip image generation and reduce costs
  ([`11c6dce`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/11c6dce3faf7343f272b339dd095a2284684e735))

- Implement no_image parameter in orchestrator for cost optimization
  ([`b882840`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/b88284009d124d166120542447dbb3432a51f1ce))

- **dry-run**: Implement dry-run mode for cost estimation and setup verification
  ([`afd2588`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/afd25884ebc5422144883b7cf691e2975d7cf493))


## v1.1.0 (2025-12-07)

### Documentation

- **phase12**: Update ROADMAP with user approval system enhancements
  ([`f73ad77`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/f73ad7733a7f69e3c25a28fd383cc3e052225d62))

### Features

- Improve fallback resilience and test infrastructure
  ([`46ee7d1`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/46ee7d1429b7707f941de876b5ef50da6301fd0a))

- **phase12**: Implement user approval system for fallback workflows with FallbackTracker
  ([`9098147`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/909814740b57dc408e5b1418724f82fea75b784c))


## v1.0.3 (2025-11-29)

### Bug Fixes

- **roadmap**: Mark Conventional Commits enforcement as completed
  ([`186f04e`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/186f04e79b27e34794a29916b0b078f847ccc84d))


## v1.0.2 (2025-11-29)

### Bug Fixes

- **errors**: Pass all args to super().__init__ and override __str__ for B042
  ([`099a764`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/099a764c3bd5bcc124428bbf8d1cb53d5aa4d61b))


## v1.0.1 (2025-11-29)

### Bug Fixes

- Pass only message to Exception.__init__ in BaseAgentError
  ([`efd9893`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/efd98931e51852d8112baa9d82b6567b4bdb3bc6))

- **lint**: Task 2 bugbear fixes (B042, B014, B011, B017)
  ([`c497f7c`](https://github.com/lilfetz22/linkedIn-post-automation-multi-agent/commit/c497f7cb5ee30b791a0094e721f3b40d7e0d5249))


## v1.0.0 (2025-11-29)

- Initial Release
