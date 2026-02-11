#!/bin/bash

# Test script to verify the improved registry client
# This script tests the reliability of the improved registry query client

set -e  # Exit on any error

echo "🧪 TESTING IMPROVED REGISTRY CLIENT"
echo "===================================="

# Configuration
REGISTRY_URL="${1:-http://localhost:3031}"
TEST_COUNT="${2:-5}"
TIMEOUT="${3:-10}"

echo "Registry URL: $REGISTRY_URL"
echo "Number of tests: $TEST_COUNT"
echo "Timeout per test: ${TIMEOUT}s"
echo ""

# Check if registry is running
echo "🔍 Checking if registry is running..."
if ! curl -s --connect-timeout 5 -X POST "$REGISTRY_URL/send" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "id": "test", "method": "ping", "params": {}}' > /dev/null 2>&1; then
    echo "❌ Registry server is NOT running on $REGISTRY_URL"
    echo "Please start the registry server first:"
    echo "  ./start_registry_server.sh"
    exit 1
fi
echo "✅ Registry server is running"
echo ""

# Test the original client
echo "🧪 Testing ORIGINAL client ($TEST_COUNT runs)..."
ORIG_SUCCESS=0
for i in $(seq 1 $TEST_COUNT); do
    echo -n "  Test $i: "
    if timeout $TIMEOUT python query_registry_client_proper.py --registry-url "$REGISTRY_URL" --timeout $((TIMEOUT-2)) >/tmp/test_orig_$i.log 2>&1; then
        echo "✅ SUCCESS"
        ((ORIG_SUCCESS++))
    else
        echo "❌ FAILED"
    fi
done

echo ""
echo "🧪 Testing IMPROVED client ($TEST_COUNT runs)..."
IMPROVED_SUCCESS=0
for i in $(seq 1 $TEST_COUNT); do
    echo -n "  Test $i: "
    if timeout $TIMEOUT python query_registry_client_proper_fixed.py --registry-url "$REGISTRY_URL" --timeout $((TIMEOUT-2)) >/tmp/test_imp_$i.log 2>&1; then
        echo "✅ SUCCESS"
        ((IMPROVED_SUCCESS++))
    else
        echo "❌ FAILED"
    fi
done

echo ""
echo "📊 TEST RESULTS SUMMARY"
echo "========================"
echo "Original client: $ORIG_SUCCESS/$TEST_COUNT successful (${ORIG_SUCCESS*100/TEST_COUNT}%)"
echo "Improved client: $IMPROVED_SUCCESS/$TEST_COUNT successful (${IMPROVED_SUCCESS*100/TEST_COUNT}%)"

echo ""
if [ $IMPROVED_SUCCESS -gt $ORIG_SUCCESS ]; then
    echo "🎉 IMPROVEMENT DETECTED!"
    improvement=$((IMPROVED_SUCCESS - ORIG_SUCCESS))
    improvement_pct=$((improvement * 100 / TEST_COUNT))
    echo "The improved client showed $improvement more successes ($improvement_pct% improvement)"
elif [ $IMPROVED_SUCCESS -eq $ORIG_SUCCESS ]; then
    echo "⚖️  NO DIFFERENCE DETECTED"
    echo "Both clients performed equally in this test"
else
    echo "⚠️  UNEXPECTED RESULT"
    echo "The original client performed better - this may indicate other factors at play"
fi

echo ""
echo "💡 RECOMMENDATION"
if [ $IMPROVED_SUCCESS -gt $ORIG_SUCCESS ]; then
    echo "Use the improved client: query_registry_client_proper_fixed.py"
    echo "Or use the improved shell wrapper: query_registry_sse_improved.sh"
else
    echo "Consider running more tests to validate the improvements"
fi

# Cleanup temporary files
rm -f /tmp/test_orig_*.log /tmp/test_imp_*.log