# Bundles

This directory contains AIGovOps bundles. A bundle is a packaged combination of skills and plugins assembled for a specific certification or compliance objective. Loading a bundle gives an agent everything it needs to operate against a defined goal (for example, ISO 42001 certification readiness or NIST AI RMF gap assessment).

Bundles are defined as `bundle.yaml` files. The YAML enumerates the constituent skills, plugins, and any bundle-specific configuration.

## Bundle index

| Bundle | Objective | Status |
|---|---|---|
| [iso42001-cert-readiness](iso42001-cert-readiness/) | Pre-certification readiness check for ISO 42001 audit | active |

## Bundle requirements

Every bundle must:

1. Live in a kebab-case directory under `bundles/`.
2. Contain a `bundle.yaml` enumerating constituent skills and plugins by name and version constraint.
3. Reference only skills and plugins that exist in this repository.
4. Be registered in the bundle index above and in the repository [README.md](../README.md).

## Bundle schema

```yaml
name: <bundle-name>
version: <semver>
description: <one-paragraph description of the bundle objective>
skills:
  - name: <skill-name>
    version: <semver-or-range>
plugins:
  - name: <plugin-name>
    version: <semver-or-range>
config:
  <bundle-specific-key>: <value>
```
