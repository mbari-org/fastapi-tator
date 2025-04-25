# CHANGELOG


## v0.7.5 (2025-04-25)

### Bug Fixes

- Correct deletion by filename endpoint and some refactored renaming for clarity
  ([`b41228f`](https://github.com/mbari-org/fastapi-tator/commit/b41228f4d4b9fdb35b389b3bd7dc194084ddb943))


## v0.7.4 (2025-04-24)

### Performance Improvements

- Add explicit logger file and try catch wrap on deletions.py
  ([`610afdb`](https://github.com/mbari-org/fastapi-tator/commit/610afdb4a00f5968401ee5b7c043e63c8e692d60))


## v0.7.3 (2025-04-14)

### Performance Improvements

- Add context manager for running init and only report verified labels for speed-up
  ([`fbf4ae3`](https://github.com/mbari-org/fastapi-tator/commit/fbf4ae392a7bb223cd58a42ddcfdadc601467064))


## v0.7.2 (2025-04-11)

### Bug Fixes

- Handle exceptions in GET labels/<project>
  ([`ef92bf7`](https://github.com/mbari-org/fastapi-tator/commit/ef92bf75996241c20a85380eb9862674435a0ba0))


## v0.7.1 (2025-04-11)

### Bug Fixes

- Correct return message formatting
  ([`371e728`](https://github.com/mbari-org/fastapi-tator/commit/371e728bb85065e8099a31f3af4732d11d08ccdb))

### Build System

- Pin to py3.10 and better recipes for install on MacOS for pysql
  ([`0a02a5f`](https://github.com/mbari-org/fastapi-tator/commit/0a02a5fabab4fb25f568707665579bd1da325eb7))


## v0.7.0 (2025-04-01)

### Features

- Added support for bulk change by cluster name and version only
  ([`2b49cfb`](https://github.com/mbari-org/fastapi-tator/commit/2b49cfb5f9cf4ed0a326effb9cdadf362732897d))


## v0.6.2 (2025-03-14)

### Performance Improvements

- Faster label query
  ([`8b183e6`](https://github.com/mbari-org/fastapi-tator/commit/8b183e67e12eecb8a6371453e6ede6d6bbd58648))


## v0.6.1 (2025-02-15)

### Bug Fixes

- Correct deletion flag which no longer requires a filter type
  ([`1385832`](https://github.com/mbari-org/fastapi-tator/commit/1385832d6fc8e19d32bd5b9f204e36e1324de9b4))

### Build System

- Added provenance and SBOM to docker build - now have an A rating in docker hub :)
  ([`48a4728`](https://github.com/mbari-org/fastapi-tator/commit/48a4728edd31d87b1cf2c803cc9a41036b6d5914))

- Remove v from docker version tag
  ([`59b1a40`](https://github.com/mbari-org/fastapi-tator/commit/59b1a40f1f9aeefea3266e90b8461db30ca9faa7))

- Simpler docker build and fix test port for docker health check
  ([`34502a6`](https://github.com/mbari-org/fastapi-tator/commit/34502a63b42c578478f3d95b7072953a52df27ec))


## v0.6.0 (2025-01-30)

### Features

- Trigger release with refactor and update screen shot of ui
  ([`ec121b4`](https://github.com/mbari-org/fastapi-tator/commit/ec121b48b06dc18a7674c24fa801f448dce72b49))


## v0.5.0 (2024-09-04)

### Features

- Added support for loading by id and version
  ([`8ecf871`](https://github.com/mbari-org/fastapi-tator/commit/8ecf871ce34a3d5c0a0c28764d2eb7778625ee07))


## v0.4.1 (2024-08-22)

### Bug Fixes

- Trigger release to update __init__.py
  ([`3a29b6d`](https://github.com/mbari-org/fastapi-tator/commit/3a29b6d1c9be805d9ca65feca84b7f467ed5d5e3))


## v0.4.0 (2024-08-13)

### Features

- Added optional localization score
  ([`11e190a`](https://github.com/mbari-org/fastapi-tator/commit/11e190a4ed91e09e0723d1a3b42ed51460e940b6))


## v0.3.0 (2024-08-09)

### Features

- Added label change by database id
  ([`5f7480f`](https://github.com/mbari-org/fastapi-tator/commit/5f7480f66d12b94811a064131ccd4152ac722b12))


## v0.2.0 (2024-08-08)

### Features

- Added label counts to /labels/{project_name}
  ([`3d605c3`](https://github.com/mbari-org/fastapi-tator/commit/3d605c3767b961967da58ad2861d919f6e4c5b6e))


## v0.1.1 (2024-08-08)

### Bug Fixes

- Correct conflicting names for getting projects
  ([`6ce93fc`](https://github.com/mbari-org/fastapi-tator/commit/6ce93fc03bf37b93e1ae3aca6c548cf095656562))


## v0.1.0 (2024-07-30)

### Documentation

- Added github repo for sdcat
  ([`b94d57b`](https://github.com/mbari-org/fastapi-tator/commit/b94d57b2224ac46d416e442a54d8e68dd7274063))

- Added missing doc images and udpated link
  ([`8b24798`](https://github.com/mbari-org/fastapi-tator/commit/8b24798372c874837902c1e2e27055c16c9072f4))

- More detail on related git repo and add license
  ([`7c53882`](https://github.com/mbari-org/fastapi-tator/commit/7c538829fd2c327a38379d552fda9fd1a6768d94))

### Features

- Initial commit
  ([`80fd459`](https://github.com/mbari-org/fastapi-tator/commit/80fd4594dc340a4d5423fbf6dc95c841b1c0c28e))
