import org.springframework.boot.gradle.plugin.SpringBootPlugin

plugins {
    `java-library`
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
}

dependencies {
    // Le BOM Spring Boot aligne Jackson, JUnit et AssertJ sur le reste du dépôt ; le scorer n'utilise pas Spring.
    implementation(platform(SpringBootPlugin.BOM_COORDINATES))
    testImplementation(platform(SpringBootPlugin.BOM_COORDINATES))

    implementation(libs.jackson.databind)
    // Quantile de la loi de Student, pour l'IC à 95 % (SPEC.md § 7).
    implementation(libs.commons.statistics.distribution)
    // Casefold Unicode complet, comme str.casefold() en Python (SPEC.md § 5).
    implementation(libs.icu4j)

    testImplementation(libs.junit.jupiter)
    testImplementation(libs.assertj.core)
    testRuntimeOnly(libs.junit.platform.launcher)
}

tasks.test {
    useJUnitPlatform()
}

tasks.processTestResources {
    // Vecteurs de conformance partagés avec le scorer Python.
    from(rootProject.file("evals/spec/tool-selection/v1")) {
        include("conformance.jsonl")
        into("tool-selection/v1")
    }
}
