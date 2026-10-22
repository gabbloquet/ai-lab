import org.springframework.boot.gradle.plugin.SpringBootPlugin

plugins {
    java
    alias(libs.plugins.spring.boot)
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(25)
    }
}

dependencies {
    implementation(platform(SpringBootPlugin.BOM_COORDINATES))
    implementation(platform(libs.spring.ai.bom))
    implementation(platform(libs.mcp.bom))
    implementation(libs.spring.ai.starter.mcp.server.webmvc)

    testImplementation(libs.spring.boot.starter.test)
    // Client MCP : les tests de contrat parlent au serveur comme un vrai client, en Streamable HTTP.
    testImplementation(libs.mcp.core)
    testRuntimeOnly(libs.junit.platform.launcher)
}

tasks.withType<JavaCompile>().configureEach {
    // Conserve les noms de paramètres : ils deviennent les noms d'arguments des outils MCP.
    options.compilerArgs.add("-parameters")
}

tasks.test {
    useJUnitPlatform()
}

tasks.processResources {
    from(rootProject.file("domains/magasin/data/v1")) { into("magasin/v1") }
}
