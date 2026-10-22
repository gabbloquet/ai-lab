plugins {
    // Télécharge le JDK de la toolchain s'il n'est pas installé sur la machine.
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

rootProject.name = "ai-lab"

dependencyResolutionManagement {
    repositories {
        mavenCentral()
    }
}

// Un module Gradle par implémentation Java d'expérience.
include("exp001-mcp-servers")
project(":exp001-mcp-servers").projectDir = file("experiments/001-mcp-outils-par-intention/java")
