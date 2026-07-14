# SPDX-License-Identifier: LGPL-2.1-or-later

file(GLOB_RECURSE Agentic_SRCS
    RELATIVE ${CMAKE_CURRENT_SOURCE_DIR}
    *.py
    *.xml
)

ADD_CUSTOM_TARGET(Agentic ALL SOURCES ${Agentic_SRCS})

fc_copy_sources(Agentic "${CMAKE_BINARY_DIR}/Mod/Agentic" ${Agentic_SRCS})

INSTALL(
    DIRECTORY
        ${CMAKE_CURRENT_SOURCE_DIR}/
    DESTINATION
        Mod/Agentic
    FILES_MATCHING
        PATTERN "*.py"
        PATTERN "*.xml"
)
