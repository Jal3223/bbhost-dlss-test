#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export CMAKE_BUILD_PARALLEL_LEVEL=${CMAKE_BUILD_PARALLEL_LEVEL:-2}
export MAKEFLAGS="-j${CMAKE_BUILD_PARALLEL_LEVEL}"
bash tools/win_deps.sh
cmake -S . -B build-win -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$PWD/cmake/mingw-toolchain.cmake" \
  -DCMAKE_PREFIX_PATH="$PWD/build/win-deps/prefix" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBBHOST_RELEASE=OFF \
  2>&1 | tee build-win-configure.log
# Optional dependencies are essential for a usable test package: fail closed.
for feature in 'libcurl .* found' 'ffmpeg found' 'SDL3 .*Vulkan found'; do
  if ! grep -Eq "bbhost: $feature" build-win-configure.log; then
    echo "Required feature missing: $feature" >&2
    exit 1
  fi
done
grep -q '^Vulkan_LIBRARY:.*=.*libvulkan-1' build-win/CMakeCache.txt
grep -q 'src/host/dlaa.cpp' build-win/build.ninja
grep -q 'src/host/frame_generation.cpp' build-win/build.ninja
grep -q 'src/host/reflex.cpp' build-win/build.ninja
cmake --build build-win --parallel "$CMAKE_BUILD_PARALLEL_LEVEL" --target \
  bbhost bb_plugin_randomizer bb_plugin_boss_rush bb_plugin_mutators bb_plugin_debug_menu \
  display_settings_test presentation_coordinates_test fg_timing_test motion_history_test \
  chromatic_stub_test ngx_transfer_sync_test \
  2>&1 | tee build-win-build.log
