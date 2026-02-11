# Troubleshooting Guide

This guide covers common failure modes you may encounter when using rentl, with clear symptom/cause/fix patterns for each.

**Start here:** Run `rentl doctor` to diagnose configuration and environment issues automatically.

---

## Missing API Key

**Symptom:**
```
Error: Connection failed: Unauthorized
```
or
```
Error: API key not configured
```

**Cause:**
The required API key environment variable is not set. Rentl needs an API key to authenticate with the translation service.

**Fix:**
1. Create or edit `.env` in your project root
2. Add your API key:
   ```
   RENTL_API_KEY=your-api-key-here
   ```
3. Run `rentl doctor` to verify the configuration

---

## Invalid or Missing Config

**Symptom:**
```
Error: Failed to parse config file
```
or
```
Error: rentl.toml not found
```
or
```
Error: Invalid TOML syntax at line X
```

**Cause:**
The `rentl.toml` configuration file is missing, has syntax errors, or contains invalid values.

**Fix:**
1. If the file is missing, run `rentl init` to create a default configuration
2. If there are syntax errors, check the TOML syntax at the reported line number
3. Verify all required fields are present (see `rentl.toml.example` for reference)
4. Run `rentl doctor` to validate your configuration

---

## Connection Failure

**Symptom:**
```
Error: Connection failed: Could not reach endpoint
```
or
```
Error: Connection timeout
```
or
```
Error: Failed to connect to https://...
```

**Cause:**
The API endpoint URL is incorrect, the service is down, or network connectivity is blocked.

**Fix:**
1. Verify the `base_url` in your `rentl.toml` configuration is correct
2. Check that the service is reachable from your network
3. Run `rentl validate-connection` to test the endpoint
4. If behind a proxy, ensure proxy settings are configured correctly

---

## Schema Version Mismatch

**Symptom:**
```
Error: Configuration schema version mismatch
```
or
```
Error: Migration needed - config format has changed
```
or
```
Error: Unsupported config version: X.Y
```

**Cause:**
Your `rentl.toml` configuration file was created with an older version of rentl and needs to be migrated to the current schema version.

**Fix:**
1. Run `rentl migrate` to automatically upgrade your configuration to the latest schema version
2. Review the changes made to `rentl.toml`
3. Run `rentl doctor` to verify the migrated configuration is valid

---

## Need More Help?

- Run `rentl doctor` for automated diagnostics
- Check command-specific help: `rentl <command> --help`
- Review the [README](../README.md) for configuration details
- Report issues at: https://github.com/trevorWieland/rentl/issues
