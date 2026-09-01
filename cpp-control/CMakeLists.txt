cmake_minimum_required(VERSION 3.16)
project(datya-control VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(OpenSSL REQUIRED)

add_executable(datya-control src/main.cpp src/event_log.cpp)
target_include_directories(datya-control PRIVATE src)
target_link_libraries(datya-control PRIVATE OpenSSL::Crypto)
target_compile_options(datya-control PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow)

install(TARGETS datya-control RUNTIME DESTINATION bin)
