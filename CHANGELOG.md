# CHANGELOG

<!-- version list -->

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
