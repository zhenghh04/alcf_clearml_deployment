#!/bin/bash
# ClearML agent environment for Tara North (ALCF GH200, north-asn-01).
#
# Tara has NO conda, NO tmux, NO crontab. Egress is PROXY-ONLY: the login node
# cannot reach amscclearml.alcf.anl.gov / PyPI directly — it must go through the
# ALCF HTTP proxy. The proxy MUST use the http:// scheme (the https:// form
# returns 000). Same proxy-at-launch fragility as Crux: without these exports the
# agent's /api/auth.login times out and the daemon exits within seconds.
# NOTE: no_proxy must NOT include .alcf.anl.gov — the ClearML server
# amscclearml.alcf.anl.gov must go THROUGH the proxy (it has no direct route).
# Adding .alcf.anl.gov here silently bypasses the proxy -> auth.login times out.
export https_proxy=http://proxy.alcf.anl.gov:3128
export http_proxy=http://proxy.alcf.anl.gov:3128
export no_proxy=localhost,127.0.0.1

# System python3 is 3.6 (too old for clearml-agent 2.0.7); the agent runs in a
# py3.11 venv built from /usr/bin/python3.11 by install (see tara/README).
source "$HOME/clearml/alcf_clearml_deployment/clients/clearml_agent_setup/tara/envs/clearml/bin/activate"
