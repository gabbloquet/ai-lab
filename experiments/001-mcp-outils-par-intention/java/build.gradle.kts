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
    // Client MCP : le test de contrat prévu parlera au serveur comme un vrai client.
    testImplementation(libs.mcp.core)
    testRuntimeOnly(libs.junit.platform.launcher)
}

tasks.withType<JavaCompile>().configureEach {
    // Conserve les noms de paramètres : ils deviennent les noms d'arguments des outils MCP.
    options.compilerArgs.add("-parameters")
}

tasks.test {
    useJUnitPlatform()
    // Prévu pour le test de contrat : il lancera le jar exécutable et lui parlera en Streamable HTTP.
    val serverJar = tasks.bootJar.flatMap { it.archiveFile }
    inputs.file(serverJar)
    jvmArgumentProviders += CommandLineArgumentProvider {
        listOf("-Dlab.server.jar=${serverJar.get().asFile.absolutePath}")
    }
}

tasks.processResources {
    from(rootProject.file("domains/magasin/data/v1")) { into("magasin/v1") }
}
